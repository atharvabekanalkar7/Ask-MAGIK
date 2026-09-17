"""
Knowledge Ingestion CLI & Pipeline
Ask MAGIK - Phase 2 RAG Engine

Usage:
    python -m backend.rag.ingest

Loads all knowledge sources from backend/knowledge/ and indexes them
into the persistent Chroma / vector store. Idempotent and safe to rerun.
"""

import sys
import time
from backend.rag.documents import load_all_knowledge_documents
from backend.rag.vector_store import PersistentVectorStore


def run_ingestion() -> int:
    """Executes the complete knowledge ingestion workflow."""
    start_time = time.time()
    print("=" * 60)
    print("Ask MAGIK Knowledge Ingestion (Phase 2 RAG Engine)")
    print("=" * 60)

    # 1. Load documents
    print("\n1. Loading knowledge files from backend/knowledge/...")
    docs = load_all_knowledge_documents()
    print(f"-> Discovered and parsed {len(docs)} knowledge chunks:")

    counts_by_type = {}
    for d in docs:
        st = d.source_type
        counts_by_type[st] = counts_by_type.get(st, 0) + 1

    for st, cnt in counts_by_type.items():
        print(f"   * {st.capitalize()}: {cnt} chunks")

    # 2. Index into vector store
    print("\n2. Indexing documents into persistent vector store...")
    store = PersistentVectorStore()
    total_indexed = store.add_documents(docs)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Knowledge Ingestion Complete!")
    print(f"Total documents in vector index: {total_indexed}")
    print(f"Persistent storage directory: {store.persist_dir}")
    print(f"Execution time: {elapsed:.2f} seconds")
    print("=" * 60)

    return total_indexed


if __name__ == "__main__":
    count = run_ingestion()
    if count == 0:
        sys.exit(1)
