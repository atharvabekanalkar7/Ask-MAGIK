"""
RAG Package for Ask MAGIK
Provides document loading, embedding, persistent vector storage, and hybrid retrieval.
"""

from .documents import KnowledgeDocument, load_all_knowledge_documents
from .embeddings import LocalEmbeddingService, get_embedding_service
from .vector_store import PersistentVectorStore
from .retriever import KnowledgeRetriever, GroundedContextPackage

__all__ = [
    "KnowledgeDocument",
    "load_all_knowledge_documents",
    "LocalEmbeddingService",
    "get_embedding_service",
    "PersistentVectorStore",
    "KnowledgeRetriever",
    "GroundedContextPackage",
]
