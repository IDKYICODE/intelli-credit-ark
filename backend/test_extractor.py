import os
from utils.document_parser import extract_text_from_pdfs
from database.vector_db import chunk_and_store_text
from agents.supervisor import GraphState
from agents.extractor import extract_financials

# 1. Locate the files in your temp_uploads folder
UPLOAD_DIR = "./temp_uploads"
test_files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]

if not test_files:
    print("❌ No PDFs found! Please drop a financial PDF into the temp_uploads folder.")
else:
    print(f"✅ Found files to test: {test_files}")
    
    # 2. Extract the text
    print("📄 Extracting document text...")
    raw_text = extract_text_from_pdfs(test_files)
    
    # 3. Seed the Vector Database!
    # (This chops the text and saves the math vectors to your hard drive)
    # 3. Seed the Vector Database!
    print("💾 Saving document chunks to ChromaDB...")
    # Extract the actual filename from the test_files array to use as the metadata tag
    source_filename = os.path.basename(test_files[0])
    chunk_and_store_text(raw_text, source_filename)
    
    # 4. Create a fake LangGraph State
    mock_state = GraphState(
        company_name="Test Corp",
        file_paths=test_files,
        raw_document_text="", # Agent 2 ignores this anyway, it talks to ChromaDB!
        document_categories={"test.pdf": "Annual Report"},
        extracted_financials={},
        external_news=[],
        swot_analysis="",
        final_recommendation="",
        next_agent=""
    )
    
    # 5. Fire the AI!
    print("🧠 Waking up Agent 2 (Gemini RAG) to extract financials...")
    result_state = extract_financials(mock_state)
    
    print("\n🎉 --- FINAL EXTRACTED FINANCIALS --- 🎉")
    import json
    print(json.dumps(result_state["extracted_financials"], indent=2))