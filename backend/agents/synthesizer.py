from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.state import GraphState
from progress import emit
from config import LLM_MODEL

llm = ChatOllama(model=LLM_MODEL, temperature=0.1)

def synthesize_report(state: GraphState) -> dict:
    session_id = state.get("session_id", "")

    emit(session_id, "synthesizer", "working", "Writing final credit memo...", "Writing memo...")

    company = state.get("company_name", "the company")
    financials = state.get("extracted_financials", {})
    news = state.get("external_news", ["No recent news found."])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a highly conservative Senior Credit Officer at a major corporate bank. Your job is to review the financial data and market news for a company, and make a final lending decision."),
        ("human", """
        Company: {company}

        Hard Financials:
        {financials}

        Recent Market Sentiment:
        {news}

        Based strictly on the data above, write a brief, professional Credit Memo.
        It must contain two things:
        1. A 3-4 sentence SWOT analysis (Strengths, Weaknesses, Opportunities, Threats).
        2. A definitive 'RECOMMENDATION: APPROVE' or 'RECOMMENDATION: REJECT' at the very end, with a 1-sentence justification.
        """)
    ])

    chain = prompt | llm
    memo = chain.invoke({
        "company": company,
        "financials": financials,
        "news": news[0] if news else "No news"
    }).content

    verdict = "APPROVED" if "APPROVE" in memo else "REJECTED"
    emit(session_id, "synthesizer", "done", f"Credit memo ready — {verdict}", verdict)

    print(f"✅ Final Credit Memo Complete.")
    return {
        "final_recommendation": memo,
        "extracted_financials": financials
    }
