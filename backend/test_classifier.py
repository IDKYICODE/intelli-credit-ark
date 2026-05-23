import os
from utils.document_parser import extract_text_from_pdfs
from agents.supervisor import GraphState
from agents.classifier import categorize_documents

# 1. Locate the files in your temp_uploads folder
UPLOAD_DIR = "./temp_uploads"
test_files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]

if not test_files:
    print("❌ No PDFs found! Please drop a PDF into the temp_uploads folder first.")
else:
    print(f"✅ Found files to test: {test_files}")
    
    # 2. Extract the text (using our new 5-page limit)
    print("📄 Extracting text from the first 5 pages...")
    raw_text = extract_text_from_pdfs(test_files)
    
    # 3. Create a fake LangGraph State to trick the agent
    mock_state = GraphState(
        company_name="Test Corp",
        file_paths=test_files,
        raw_document_text=raw_text,
        document_categories={},
        extracted_financials={},
        external_news=[],
        swot_analysis="",
        final_recommendation="",
        next_agent=""
    )
    
    # 4. Fire the AI!
    print("🧠 Waking up Agent 1 (Gemini) to classify...")
    result_state = categorize_documents(mock_state)
    
    print("\n🎉 --- FINAL RESULT --- 🎉")
    print(result_state)