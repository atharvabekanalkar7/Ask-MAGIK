"""
Persistent Vector Store
Ask MAGIK - Phase 2 RAG Engine

Manages persistent indexing and retrieval of knowledge documents.
Integrates with ChromaDB when available, and provides an embedded persistent
cosine vector store in backend/rag/chroma_db/ for guaranteed local offline execution.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from backend.config import settings
from backend.rag.documents import KnowledgeDocument
from backend.rag.embeddings import get_embedding_service


class PersistentVectorStore:
    """Manages document embeddings and similarity search with persistence."""

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.resolved_chroma_path
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.store_file = self.persist_dir / "knowledge_store.json"
        self.embedder = get_embedding_service()
        self.chroma_client = None
        self.chroma_collection = None
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []

        self._init_chroma_or_fallback()

    def _init_chroma_or_fallback(self):
        """Attempts to connect to ChromaDB, falls back to embedded persistent storage."""
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name="skyline_knowledge",
                metadata={"description": "Skyline Telecom DataMart Knowledge Base"}
            )
            print("[VectorStore] Connected to ChromaDB persistent collection.")
        except Exception as e:
            print(f"[VectorStore] ChromaDB package not active ({e}); using embedded persistent vector store.")
            self.chroma_client = None
            self.chroma_collection = None
            self._load_local_store()

    def _load_local_store(self):
        """Loads documents and cached embeddings from persistent JSON file."""
        if self.store_file.exists():
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.doc_ids = list(self.documents.keys())
                    if self.doc_ids:
                        vectors = [self.documents[doc_id]["vector"] for doc_id in self.doc_ids]
                        self.embeddings_matrix = np.array(vectors, dtype=np.float32)
                print(f"[VectorStore] Loaded {len(self.documents)} documents from {self.store_file.name}")
            except Exception as e:
                print(f"[VectorStore] Error loading local store: {e}")
                self.documents = {}
                self.doc_ids = []
                self.embeddings_matrix = None

    def _save_local_store(self):
        """Saves current state to local JSON file."""
        data = {"documents": self.documents}
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_documents(self, docs: List[KnowledgeDocument]) -> int:
        """
        Indexes knowledge documents. Idempotent: updates existing or appends new.
        Returns the total count of documents in the store.
        """
        if not docs:
            return self.count()

        texts = [doc.content for doc in docs]
        vectors = self.embedder.encode(texts)

        if self.chroma_collection is not None:
            # ChromaDB ingestion
            ids = [doc.doc_id for doc in docs]
            metadatas = [
                {
                    "source_type": doc.source_type,
                    "table": doc.table,
                    "document_name": doc.document_name,
                    "category": doc.category,
                    **(doc.metadata or {})
                }
                for doc in docs
            ]
            # Convert list metadatas to strings for Chroma compatibility if needed
            cleaned_meta = []
            for m in metadatas:
                cleaned = {}
                for k, v in m.items():
                    cleaned[k] = json.dumps(v) if isinstance(v, (list, dict)) else str(v)
                cleaned_meta.append(cleaned)

            self.chroma_collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=vectors.tolist(),
                metadatas=cleaned_meta,
            )
            print(f"[VectorStore] Upserted {len(docs)} documents into ChromaDB.")

        # Also maintain local store representation for offline consistency
        for idx, doc in enumerate(docs):
            self.documents[doc.doc_id] = {
                "doc_id": doc.doc_id,
                "content": doc.content,
                "source_type": doc.source_type,
                "table": doc.table,
                "document_name": doc.document_name,
                "category": doc.category,
                "metadata": doc.metadata,
                "vector": vectors[idx].tolist(),
            }

        self.doc_ids = list(self.documents.keys())
        all_vecs = [self.documents[did]["vector"] for did in self.doc_ids]
        self.embeddings_matrix = np.array(all_vecs, dtype=np.float32)
        self._save_local_store()

        return self.count()

    def search(
        self,
        query: str,
        top_k: int = 8,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs cosine similarity search against indexed knowledge.
        Returns list of matching document dicts with similarity scores.
        """
        if self.count() == 0:
            return []

        query_vector = self.embedder.encode(query)

        # 1. If Chroma collection exists and is available
        if self.chroma_collection is not None:
            try:
                where_clause = {"source_type": source_type} if source_type else None
                results = self.chroma_collection.query(
                    query_embeddings=[query_vector.tolist()],
                    n_results=min(top_k, self.count()),
                    where=where_clause,
                )
                hits = []
                ids = results["ids"][0]
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results.get("distances", [[0.0] * len(ids)])[0]

                for i, doc_id in enumerate(ids):
                    # Convert cosine distance to similarity score
                    dist = distances[i] if distances else 0.0
                    similarity = 1.0 - (dist / 2.0)
                    hits.append({
                        "doc_id": doc_id,
                        "content": docs[i],
                        "source_type": metas[i].get("source_type", "unknown"),
                        "table": metas[i].get("table", ""),
                        "document_name": metas[i].get("document_name", ""),
                        "category": metas[i].get("category", ""),
                        "metadata": metas[i],
                        "similarity": round(float(similarity), 4),
                    })
                return hits
            except Exception as e:
                print(f"[VectorStore] Chroma query fallback to local store: {e}")

        # 2. Local cosine similarity computation
        if self.embeddings_matrix is None or len(self.doc_ids) == 0:
            return []

        q_norm = np.linalg.norm(query_vector)
        if q_norm > 1e-9:
            q_normed = query_vector / q_norm
        else:
            q_normed = query_vector

        # Dot product with normalized matrix gives cosine similarity
        similarities = np.dot(self.embeddings_matrix, q_normed)

        # Filter by source_type if specified
        indices = np.argsort(similarities)[::-1]
        hits = []

        for idx in indices:
            did = self.doc_ids[idx]
            doc = self.documents[did]
            if source_type and doc.get("source_type") != source_type:
                continue

            hits.append({
                "doc_id": did,
                "content": doc["content"],
                "source_type": doc.get("source_type", "unknown"),
                "table": doc.get("table", ""),
                "document_name": doc.get("document_name", ""),
                "category": doc.get("category", ""),
                "metadata": doc.get("metadata", {}),
                "similarity": round(float(similarities[idx]), 4),
            })
            if len(hits) >= top_k:
                break

        return hits

    def count(self) -> int:
        """Returns the total number of indexed documents."""
        if self.chroma_collection is not None:
            try:
                return self.chroma_collection.count()
            except Exception:
                pass
        return len(self.documents)

    def get_status(self) -> Dict[str, Any]:
        """Returns operational status of the vector store."""
        return {
            "status": "ready" if self.count() > 0 else "empty",
            "document_count": self.count(),
            "storage_mode": "chromadb" if self.chroma_collection else "local_vector_store",
            "persist_path": str(self.persist_dir),
            "embedding_dimension": self.embedder.dimension,
        }
