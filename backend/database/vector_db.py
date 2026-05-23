import os
import time
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "financial_documents"

# Load once at startup — BAAI/bge-large-en-v1.5 is ~1.3GB, reloading per call is brutal
_embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    encode_kwargs={"batch_size": 64, "normalize_embeddings": True},
)

def get_vector_store():
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_embeddings,
        persist_directory=CHROMA_PATH
    )

def chunk_and_store_text(raw_text: str, source_name: str):
    if not raw_text.strip():
        print("Warning: No text provided to chunk.")
        return

    t0 = time.perf_counter()
    print("🔪 Chopping document into smaller chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        length_function=len,
        add_start_index=True,
    )

    chunks = text_splitter.split_text(raw_text)
    metadatas = [{"source": source_name} for _ in chunks]
    print(f"⏱  Chunking:     {time.perf_counter()-t0:.2f}s  ({len(chunks)} chunks)")

    vector_store = get_vector_store()

    try:
        vector_store.delete_collection()
        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_embeddings,
            persist_directory=CHROMA_PATH
        )
        print("🗑️  Cleared old collection.")
    except Exception as e:
        print(f"Warning: Could not clear old collection: {e}")

    print(f"🧠 Embedding {len(chunks)} chunks with bge-small (batch=64)...")
    t1 = time.perf_counter()
    vector_store.add_texts(texts=chunks, metadatas=metadatas)
    print(f"⏱  Embedding:    {time.perf_counter()-t1:.2f}s  ({len(chunks)} chunks @ batch=16)")
    print(f"⏱  Total store:  {time.perf_counter()-t0:.2f}s")