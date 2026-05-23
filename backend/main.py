import os
import shutil
import asyncio
import json
from typing import List
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from progress import init_session, mark_done, get_events

# --- 1. SQLITE IMPORTS (For saving company details) ---
from models.schemas import EntityOnboardingCreate, EntityResponse
from database.sqlite_db import init_db, get_db, CompanyEntity

# --- 2. LANGGRAPH IMPORTS (For the AI Pipeline) ---
from utils.document_parser import extract_text_from_pdfs
from database.vector_db import chunk_and_store_text
from agents.supervisor import ark_pipeline
from agents.state import GraphState  # Using the clean import from our circular dependency fix!

app = FastAPI(title="ARK Intelli-Credit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQL Database
init_db()

UPLOAD_DIRECTORY = "./temp_uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True) 

@app.get("/")
def health_check():
    return {"status": "ARK Backend is alive and running!"}

# -----------------------------------------------------------------
# STAGE 1: Real Database Save Endpoint
# -----------------------------------------------------------------
@app.post("/api/onboard", response_model=EntityResponse)
def onboard_entity(entity: EntityOnboardingCreate, db: Session = Depends(get_db)):
    """
    Catches the JSON from React, converts it to a SQLAlchemy model, 
    and permanently saves it to the SQLite database.
    """
    print(f"Saving {entity.company_name} to the database...")
    
    existing_company = db.query(CompanyEntity).filter(CompanyEntity.cin == entity.cin).first()
    if existing_company:
        raise HTTPException(status_code=400, detail="A company with this CIN already exists.")
    
    db_company = CompanyEntity(
        company_name=entity.company_name,
        cin=entity.cin,
        pan=entity.pan,
        sector=entity.sector,
        loan_type=entity.loan_type,
        loan_amount=entity.loan_amount,
        loan_tenure_months=entity.loan_tenure_months
    )
    
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    print(f"✅ Saved successfully with ID: {db_company.id}")
    
    return db_company

@app.get("/api/companies", response_model=List[EntityResponse])
def get_all_companies(db: Session = Depends(get_db)):
    """
    Fetches every single company that has been saved to the SQLite database.
    """
    companies = db.query(CompanyEntity).all()
    return companies

# -----------------------------------------------------------------
# SSE: Real-time agent status stream
# -----------------------------------------------------------------
@app.get("/api/status/{session_id}")
async def status_stream(session_id: str):
    async def generate():
        sent = 0
        for _ in range(1500):  # max ~5 min polling
            for ev in get_events(session_id, sent):
                yield f"data: {json.dumps(ev)}\n\n"
                sent += 1
                if ev.get("done"):
                    return
            await asyncio.sleep(0.2)
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Access-Control-Allow-Origin": "*"},
    )

# -----------------------------------------------------------------
# STAGE 2: File Upload Endpoint (AI Pipeline)
# -----------------------------------------------------------------
@app.post("/api/upload-documents")
async def upload_documents(session_id: str = Query(default=""), files: List[UploadFile] = File(...)):
    try:
        if session_id:
            init_session(session_id)

        # 1. Clean the temp folder of old PDFs
        for filename in os.listdir(UPLOAD_DIRECTORY):
            file_path = os.path.join(UPLOAD_DIRECTORY, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        # 2. Save the new PDF
        saved_file_paths = []
        for file in files:
            file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
            with open(file_location, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_file_paths.append(file_location)

        # 3. Extract Text
        print(f"📄 Extracting text from {len(saved_file_paths)} file(s)...")
        raw_text = extract_text_from_pdfs(saved_file_paths)

        # 4. Save to ChromaDB
        print("💾 Saving document chunks to ChromaDB...")
        chunk_and_store_text(raw_text, files[0].filename)

        # 5. Build the Clipboard for LangGraph
        initial_state = GraphState(
            session_id=session_id,
            company_name="Unknown",
            file_paths=saved_file_paths,
            raw_document_text=raw_text,
            document_categories={},
            extracted_financials={},
            external_news=[],
            swot_analysis="",
            final_recommendation="",
            next_agent=""
        )

        # 6. Run the AI pipeline in a thread so SSE can stream concurrently
        print("🚀 Waking up the LangGraph Supervisor...")
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(None, lambda: ark_pipeline.invoke(initial_state))

        if session_id:
            mark_done(session_id)

        # 7. Send the JSON back to React
        return {
            "message": "Analysis complete!",
            "company_name": final_state.get("company_name", "Unknown"),
            "categories": final_state.get("document_categories", {}),
            "financials": final_state.get("extracted_financials", {}),
            "external_news": final_state.get("external_news", []),
            "final_recommendation": final_state.get("final_recommendation", "")
        }

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))