from duckduckgo_search import DDGS
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.state import GraphState
from progress import emit
from config import LLM_MODEL

llm = ChatOllama(model=LLM_MODEL, temperature=0.3)

def research_company(state: GraphState) -> dict:
    session_id = state.get("session_id", "")

    emit(session_id, "researcher", "working", "Identifying company from document...", "Identifying...")

    raw_text = state.get("raw_document_text", "")

    name_prompt = f"Read this excerpt from a financial document. What is the name of the main company this document is about? Return ONLY the company name, nothing else. Excerpt: {raw_text[:2000]}"

    company_name = llm.invoke(name_prompt).content.strip()

    emit(session_id, "researcher", "working", f"Searching news for {company_name}...", "Searching...")

    search_query = f"{company_name} latest financial news stock market"

    formatted_search_results = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=3))
            for r in results:
                formatted_search_results += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
    except Exception as e:
        print(f"Warning: Web search failed. {e}")
        formatted_search_results = "No recent news found."

    emit(session_id, "researcher", "working", "Synthesizing market sentiment...", "Analyzing news...")

    print("🧠 Synthesizing market sentiment...")
    summary_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior financial risk analyst. Read the following recent news search results about {company}. Write a concise, 3-4 sentence summary of the current market sentiment, highlighting any major risks, lawsuits, or positive tailwinds."),
        ("human", "Web Search Results:\n{news_data}")
    ])

    chain = summary_prompt | llm
    sentiment_summary = chain.invoke({"company": company_name, "news_data": formatted_search_results}).content

    emit(session_id, "researcher", "done", f"Sentiment analyzed for {company_name}", f"{company_name[:18]} done")

    return {
        "company_name": company_name,
        "external_news": [sentiment_summary],
        "extracted_financials": state.get("extracted_financials", {})
    }
