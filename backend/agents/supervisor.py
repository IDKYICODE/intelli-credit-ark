from langgraph.graph import StateGraph, START, END

from agents.state import GraphState  # <-- Importing the clipboard from the new file!
from agents.classifier import categorize_documents
from agents.extractor import extract_financials
from agents.researcher import research_company
from agents.synthesizer import synthesize_report

def route_document(state: GraphState) -> str:
    print("🚦 SUPERVISOR: Making a routing decision...")
    
    categories = state.get("document_categories", {})
    print(f"   [Debug] The Classifier returned: {categories}")
    
    # THE FIX: Convert the entire dictionary into one massive lowercase string
    cat_string = str(categories).lower()
    
    # Now we just check if the magic words exist *anywhere* in that string
    if any(word in cat_string for word in ["annual", "report", "financial", "bank", "statement", "true"]):
        print("➡️ Route: Financial document detected. Sending to Extractor.")
        return "extractor"
    
    print("➡️ Route: No financials detected. Skipping Extractor, sending straight to Researcher.")
    return "researcher"

workflow = StateGraph(GraphState)

workflow.add_node("classifier", categorize_documents)
workflow.add_node("extractor", extract_financials)
workflow.add_node("researcher", research_company)
workflow.add_node("synthesizer", synthesize_report)

workflow.add_edge(START, "classifier")

workflow.add_conditional_edges(
    "classifier",
    route_document,
    {
        "extractor": "extractor",
        "researcher": "researcher"
    }
)

workflow.add_edge("extractor", "researcher")
workflow.add_edge("researcher", "synthesizer")
workflow.add_edge("synthesizer", END)

ark_pipeline = workflow.compile()