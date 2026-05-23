# backend/agents/state.py
from typing import TypedDict, List

class GraphState(TypedDict):
    session_id: str
    company_name: str
    file_paths: List[str]
    raw_document_text: str
    document_categories: dict
    extracted_financials: dict
    external_news: List[str]
    swot_analysis: str
    final_recommendation: str
    next_agent: str