from langchain_community.document_loaders import PyPDFLoader
import os
import time

import re

_ANCHORS = [
    "total assets", "total liabilities", "shareholders equity", "total equity",
    "total borrowings", "long-term borrowings", "short-term borrowings",
    "revenue from operations", "total income", "total revenue",
    "profit before tax", "profit after tax", "profit for the year",
    "net cash", "operating activities", "investing activities", "financing activities",
    "balance sheet", "statement of profit and loss", "cash flow statement",
    "earnings per share", "total expenses", "ebitda",
]

def _normalize_for_score(text: str) -> str:
    """Basic normalization to improve anchor matching."""
    text = text.lower()
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    # collapse "t otal" -> "total"
    text = re.sub(r"\b([a-z])\s+([a-z])", r"\1\2", text)
    return text

def _anchor_score(text: str) -> float:
    norm = _normalize_for_score(text)
    return sum(5 for phrase in _ANCHORS if phrase in norm)

SHORT_DOC_THRESHOLD = 80   # pages — bank statements, shareholding patterns stay under this
MAX_PAGES = 150            # max pages to embed for large docs (Increased from 60)
CONTINUATION_PAGES = 5    # pages after each anchor to capture table continuations

def _select_pages_large_doc(pages: list, total: int) -> list:
    anchor_indices = {
        i for i, p in enumerate(pages)
        if _anchor_score(p.page_content) >= 10
    }
    expanded = set()
    for idx in anchor_indices:
        for j in range(idx, min(idx + CONTINUATION_PAGES + 1, total)):
            expanded.add(j)
    
    # Fallback if anchors found nothing
    if len(expanded) < 10:
        scores = sorted(range(total), key=lambda i: _anchor_score(pages[i].page_content), reverse=True)
        for i in scores[:MAX_PAGES]:
            expanded.add(i)
    
    # If we have too many pages, we should still try to keep the ones with highest scores
    # but for now let's just increase the limit and see if it helps.
    # We sort them to keep the document order.
    kept_indices = sorted(expanded)
    
    if len(kept_indices) > MAX_PAGES:
        # Instead of just [:MAX_PAGES], we take the ones with highest anchor scores.
        scored_indices = sorted(kept_indices, key=lambda i: _anchor_score(pages[i].page_content), reverse=True)
        kept_indices = sorted(scored_indices[:MAX_PAGES])

    return kept_indices, len(anchor_indices)

def extract_text_from_pdfs(file_paths: list[str]) -> str:
    combined_text = ""

    for path in file_paths:
        if not os.path.exists(path):
            print(f"Warning: Could not find file at {path}")
            continue

        try:
            t0 = time.perf_counter()
            loader = PyPDFLoader(path)
            pages = loader.load()
            total = len(pages)
            print(f"⏱  PDF load:     {time.perf_counter()-t0:.2f}s  ({total} pages)")

            t1 = time.perf_counter()

            if total <= SHORT_DOC_THRESHOLD:
                # Short doc: keep all pages (bank statement, shareholding, etc.)
                kept = pages
                print(f"⏱  Page filter:  {time.perf_counter()-t1:.2f}s  (short doc — all {total} pages kept)")
            else:
                # Large doc: anchor scoring + continuation (annual reports)
                kept_indices, anchor_count = _select_pages_large_doc(pages, total)
                kept = [pages[i] for i in kept_indices]
                print(f"⏱  Page scoring: {time.perf_counter()-t1:.2f}s  ({anchor_count} anchors → {len(kept)}/{total} kept)")

            combined_text += f"\n\n--- Start of Document: {os.path.basename(path)} ---\n\n"
            for page in kept:
                combined_text += page.page_content + "\n"

        except Exception as e:
            print(f"Error reading {path}: {str(e)}")

    return combined_text
