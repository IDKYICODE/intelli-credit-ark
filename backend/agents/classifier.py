from pydantic import BaseModel, Field
from typing import Dict
import json
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from agents.state import GraphState
from progress import emit
from config import LLM_MODEL

class ClassificationResult(BaseModel):
    categories: Dict[str, str] = Field(
        description="Dictionary mapping filenames to categories: 'ALM', 'Shareholding', 'Annual Report', 'Bank Statement', or 'Unknown'."
    )

llm = ChatOllama(model=LLM_MODEL, temperature=0, format="json")

def categorize_documents(state: GraphState) -> dict:
    session_id = state.get("session_id", "")
    emit(session_id, "classifier", "working", "Reading uploaded documents...", "Classifying...")

    raw_text = state.get("raw_document_text", "")
    file_paths = state.get("file_paths", [])
    filenames = [os.path.basename(p) for p in file_paths]

    if not raw_text:
        emit(session_id, "classifier", "done", "No text found", "No text")
        return {"document_categories": {}}

    system_prompt = """
    You are an expert Credit Analyst. Your task is to classify these specific filenames: {filenames}
    
    CRITICAL: You MUST return a JSON object with EXACTLY this structure:
    {{
      "categories": {{
        "filename.pdf": "Category"
      }}
    }}
    
    The keys in 'categories' MUST be the exact filenames provided.
    The values MUST be one of these EXACT categories:
    'ALM', 'Shareholding', 'Annual Report', 'Bank Statement', or 'Unknown'.

    Analyze the following document text to determine the category for each file:
    {document_text}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Classify these specific files now: {filenames}. Return ONLY JSON.")
    ])

    chain = prompt | llm

    print("Asking Qwen to classify...")
    # Since we use format="json", we'll get a JSON string or dict back
    response = chain.invoke({"document_text": raw_text[:20000], "filenames": filenames}) 

    try:

        if isinstance(response.content, str):
            data = json.loads(response.content)
        else:
            data = response.content

        # Fallback: if LLM returns a list of files instead of a dict
        if "categories" in data:
            categories = data["categories"]
        elif "files" in data:
            # Fallback for the structure we saw in the logs
            categories = {}
            for f in data["files"]:
                name = f.get("name")
                # Try to match the name back to our filenames
                matched_filename = next((fn for fn in filenames if name in fn or fn in name), filenames[0])
                cat = f.get("type", "Unknown").replace("_", " ").title()
                if cat == "Annual_Report": cat = "Annual Report"
                if cat == "Bank_Statement": cat = "Bank Statement"
                categories[matched_filename] = cat
        else:
            categories = data
    except Exception as e:
        print(f"Error parsing classification: {e}")
        categories = {f: "Unknown" for f in filenames}

    categories_str = ", ".join(categories.values()) if categories else "Unknown"
    emit(session_id, "classifier", "done", f"Classified: {categories_str}", categories_str[:22])

    print(f"Classification Complete: {categories}")
    return {"document_categories": categories}
