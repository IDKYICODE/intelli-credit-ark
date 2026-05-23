import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from agents.state import GraphState
from database.vector_db import get_vector_store
from progress import emit
from config import LLM_MODEL

text_llm = ChatOllama(model=LLM_MODEL, temperature=0)

# Indian number: 1,40,804.53 or 40,804 or 1,40,804
_NUM = r"([\d,]+\.?\d*)"

# PDF OCR artifacts: "T otal" "proﬁt" "ﬁnancial" — handle by making spaces optional
# and replacing ligatures before search
def _normalize(text: str) -> str:
    """Normalize PDF OCR artifacts for reliable matching."""
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")
    text = text.replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    # collapse "T otal" → "Total", "P rofit" → "Profit" etc.
    text = re.sub(r"\b([A-Z])\s+([a-z])", r"\1\2", text)
    return text


def _window_around(text: str, idx: int, before: int = 80, after: int = 600) -> str:
    return text[max(0, idx - before): min(len(text), idx + after)]


def _find_sections(norm_text: str, patterns: list[str], window: int = 600) -> str:
    """Return joined text windows around each pattern match."""
    snippets = []
    for pat in patterns:
        for m in re.finditer(pat, norm_text, re.IGNORECASE):
            snippet = _window_around(norm_text, m.start(), after=window)
            if snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= 5:
                return "\n\n---\n\n".join(snippets)
    return "\n\n---\n\n".join(snippets)


# --- Regex direct extractors (fast, no LLM needed) ---

def _try_regex(norm_text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        m = re.search(pat, norm_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().rstrip(",")
            if val:
                return val
    return None


METRICS = [
    {
        "id": "total_revenue",
        "section_patterns": [
            r"Total\s+revenue\s+from\s+operations",
            r"Revenue\s+from\s+operations",
            r"Total\s+income",
        ],
        "regex_patterns": [
            r"Total\s+revenue\s+from\s+operations\s+" + _NUM,
            r"Total\s+income\s+" + _NUM,
        ],
        "prompt": (
            "Extract ONLY 'Total Revenue from Operations' or 'Total Income' "
            "for the year ended 31 March 2025 from the Consolidated P&L.\n"
            "Amounts are in Indian Rupees in lakhs. Indian format: 1,40,804.53\n"
            "If two columns exist (FY25 | FY24), pick FY25 (left column).\n"
            "Reply with ONLY the number, e.g.: 1,40,804.53 lakhs\n"
            "If not found: Not Found"
        ),
    },
    {
        "id": "net_profit",
        "section_patterns": [
            r"Net\s+profit\s+after\s+tax",
            r"Net\s+\(loss\)\s*/\s*profit\s+after\s+tax",
            r"Profit\s+for\s+the\s+year",
        ],
        "regex_patterns": [
            r"Net\s+\(?loss\)?\s*/?\s*profit\s+after\s+tax\s+(?:for\s+the\s+year\s+)?" + _NUM,
            r"Net\s+profit\s+after\s+tax\s+(?:for\s+the\s+year\s+)?" + _NUM,
            r"Profit\s+for\s+the\s+year\s+" + _NUM,
        ],
        "prompt": (
            "Extract ONLY 'Net Profit After Tax' or 'Profit for the Year' "
            "for the year ended 31 March 2025 from the Consolidated P&L.\n"
            "Amounts in lakhs. If two columns (FY25 | FY24), pick FY25.\n"
            "Reply with ONLY the number, e.g.: 35,878.17 lakhs\n"
            "If not found: Not Found"
        ),
    },
    {
        "id": "total_debt",
        "section_patterns": [
            r"Debt\s+securities",
            r"Borrowings\s+\(Other\s+than",
            r"Total\s+borrowings",
        ],
        "regex_patterns": [
            # total borrowings as single line
            r"Total\s+borrowings\s+" + _NUM,
        ],
        "prompt": (
            "Find 'Debt Securities' AND 'Borrowings (Other than Debt Securities)' "
            "from the Consolidated Balance Sheet as at 31 March 2025.\n"
            "Sum both values to give Total Debt. Amounts in lakhs.\n"
            "If two columns (Mar-25 | Mar-24), use Mar-25.\n"
            "Reply ONLY: <summed total> lakhs, e.g.: 8,04,344.82 lakhs\n"
            "If not found: Not Found"
        ),
    },
    {
        "id": "cash_and_equivalents",
        "section_patterns": [
            r"Cash\s+and\s+cash\s+equivalents\s+at\s+the\s+end",
            r"Total\s+cash\s+and\s+cash\s+equivalents",
            r"Cash\s+and\s+cash\s+equivalents",
        ],
        "regex_patterns": [
            r"Cash\s+and\s+cash\s+equivalents\s+at\s+the\s+end\s+of\s+the\s+year\s+" + _NUM,
            r"Total\s+cash\s+and\s+cash\s+equivalents\s+" + _NUM,
        ],
        "prompt": (
            "Extract 'Cash and Cash Equivalents at the end of the year' "
            "from the Consolidated Cash Flow Statement for 31 March 2025.\n"
            "Amounts in lakhs. If two columns, use FY25 (left).\n"
            "Reply ONLY: <number> lakhs, e.g.: 31,807.17 lakhs\n"
            "If not found: Not Found"
        ),
    },
    {
        "id": "total_credits",
        "section_patterns": [
            r"Total\s+credits",
            r"Sum\s+of\s+credits",
            r"Total\s+deposits",
        ],
        "regex_patterns": [
            r"Total\s+credits[:\s]+" + _NUM,
            r"Total\s+deposits[:\s]+" + _NUM,
        ],
        "prompt": (
            "Extract 'Total Credits' or 'Total Deposits' from the Bank Statement.\n"
            "This is the sum of all money coming into the account.\n"
            "Reply with ONLY the number, e.g.: 15,20,450.00\n"
            "If not found: Not Found"
        ),
    },
    {
        "id": "total_debits",
        "section_patterns": [
            r"Total\s+debits",
            r"Sum\s+of\s+debits",
            r"Total\s+withdrawals",
        ],
        "regex_patterns": [
            r"Total\s+debits[:\s]+" + _NUM,
            r"Total\s+withdrawals[:\s]+" + _NUM,
        ],
        "prompt": (
            "Extract 'Total Debits' or 'Total Withdrawals' from the Bank Statement.\n"
            "This is the sum of all money going out of the account.\n"
            "Reply with ONLY the number, e.g.: 12,10,200.00\n"
            "If not found: Not Found"
        ),
    },
]


def _rag_context(vector_store, queries: list[str], k: int = 10) -> str:
    seen, docs = set(), []
    per_query = max(2, k // len(queries))
    for q in queries:
        try:
            results = vector_store.similarity_search(q, k=per_query)
            for doc in results:
                if doc.page_content not in seen:
                    seen.add(doc.page_content)
                    docs.append(doc)
        except Exception as e:
            print(f"  RAG failed: {e}")
    return "\n\n---\n\n".join(d.page_content for d in docs[:k])


def _llm_extract(context: str, prompt_text: str, metric_id: str) -> str:
    if not context.strip():
        print(f"  [{metric_id}] empty context, skipping LLM")
        return "Not Found"
    
    # Force the LLM to be extremely concise and follow instructions
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a precise financial data extractor. Respond ONLY with the requested value or 'Not Found'. Do NOT explain. Do NOT include any other text."),
        ("human", f"INSTRUCTION: {prompt_text}\n\nDOCUMENT EXCERPTS:\n{context}\n\nValue?"),
    ])
    try:
        raw = (prompt | text_llm).invoke({}).content.strip()
        # Take the first line and try to extract a number if it looks like a sentence
        raw = raw.split("\n")[0].strip()
        
        if any(w in raw.lower() for w in ("not found", "missing", "unavailable", "cannot", "no data")):
            return "Not Found"
            
        # If the response is too long, it's likely conversational; try to extract just the number
        if len(raw) > 30:
            match = re.search(r"(\d[\d,.]*\d|\d)\s*(?:lakhs|INR|Rupees|units)?", raw, re.IGNORECASE)
            if match:
                raw = match.group(0)
            else:
                return "Not Found"
                
        return raw
    except Exception as e:
        print(f"  LLM error [{metric_id}]: {e}")
        return "Not Found"


def extract_financials(state: GraphState) -> dict:
    session_id = state.get("session_id", "")
    emit(session_id, "extractor", "working", "Searching document...", "Extracting...")

    raw_text = state.get("raw_document_text", "")

    norm_text = _normalize(raw_text)
    vector_store = get_vector_store()
    extracted_data = {}

    for metric in METRICS:
        mid = metric["id"]

        # Step 1: fast regex on normalized text (if available)
        val = None
        if norm_text:
            val = _try_regex(norm_text, metric["regex_patterns"])
        
        if val:
            # Don't add 'lakhs' if it's already there or if it's a bank statement value
            if "lakhs" not in val.lower() and mid not in ["total_credits", "total_debits"]:
                val = val + " lakhs"
            print(f"  [{mid}] regex hit → {val}")
        else:
            print(f"  [{mid}] regex miss → trying LLM with keyword context")
            # Step 2: find surrounding sections, send to LLM
            ctx = ""
            if norm_text:
                ctx = _find_sections(norm_text, metric["section_patterns"])
            
            if ctx:
                print(f"  [{mid}] context length: {len(ctx)} chars")
                val = _llm_extract(ctx, metric["prompt"], mid)
            else:
                val = "Not Found"

            # Step 3: RAG fallback
            if val == "Not Found":
                print(f"  [{mid}] keyword context miss → trying RAG")
                rag_ctx = _rag_context(vector_store, metric["section_patterns"])
                val = _llm_extract(_normalize(rag_ctx), metric["prompt"], mid)

        extracted_data[mid] = val

    revenue = extracted_data.get("total_revenue", "N/A")
    # If revenue is N/A, maybe show credits if it's a bank statement
    if revenue == "Not Found" or revenue == "N/A":
        credits = extracted_data.get("total_credits", "N/A")
        if credits != "Not Found" and credits != "N/A":
            revenue = f"Credits: {credits}"

    emit(session_id, "extractor", "done", f"Revenue/Credits: {revenue}", f"Res: {str(revenue)[:16]}")
    return {"extracted_financials": extracted_data}
