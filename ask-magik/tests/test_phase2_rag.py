"""
Phase 2 Tests: RAG Ingestion & Vector Retrieval
"""

import pytest
from backend.rag.documents import load_all_knowledge_documents
from backend.rag.vector_store import PersistentVectorStore
from backend.rag.retriever import KnowledgeRetriever


def test_knowledge_document_loading():
    """Verifies knowledge documents are loaded and parsed with metadata."""
    docs = load_all_knowledge_documents()
    assert len(docs) >= 40, f"Expected at least 40 chunks, found {len(docs)}"

    source_types = set(d.source_type for d in docs)
    assert "schema" in source_types
    assert "glossary" in source_types
    assert "business_rule" in source_types
    assert "example" in source_types


def test_vector_store_indexing_and_count():
    """Verifies persistent vector store indexing is non-empty and idempotent."""
    store = PersistentVectorStore()
    count = store.count()
    assert count >= 45, f"Expected at least 45 indexed documents, found {count}"

    status = store.get_status()
    assert status["status"] == "ready"
    assert status["document_count"] == count


def test_rag_retrieval_for_prepaid_churn():
    """Verifies retrieval for prepaid churn returns subscriber_profile and churn_events."""
    retriever = KnowledgeRetriever()
    pkg = retriever.retrieve("Which prepaid plans had the highest customer loss in the western region last month?")
    assert len(pkg.chunks) > 0
    assert any("churn" in c["content"].lower() or "prepaid" in c["content"].lower() for c in pkg.chunks)
    assert any(t in pkg.top_tables for t in ["subscriber_profile", "churn_events"])


def test_rag_retrieval_for_ramadan_campaign():
    """Verifies retrieval for Ramadan campaign retrieves campaign_response context."""
    retriever = KnowledgeRetriever()
    pkg = retriever.retrieve("How did the Ramadan data-bundle campaign perform compared to last year by region?")
    assert len(pkg.chunks) > 0
    assert any("ramadan" in c["content"].lower() or "campaign" in c["content"].lower() for c in pkg.chunks)
    assert "campaign_response" in pkg.top_tables


def test_rag_retrieval_for_small_business_usage():
    """Verifies retrieval for small business usage decline."""
    retriever = KnowledgeRetriever()
    pkg = retriever.retrieve("Show me postpaid small-business customers whose usage dropped more than 30%.")
    assert len(pkg.chunks) > 0
    assert any("usage" in c["content"].lower() or "small business" in c["content"].lower() for c in pkg.chunks)
