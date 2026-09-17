"""
Hybrid Knowledge Retriever
Ask MAGIK - Phase 2 RAG Engine

Combines dense vector similarity with keyword/exact-match boosting
for telecom domain entities (tables, columns, glossary terms, campaign names).
Constructs an organized, grounded context package for LLM SQL generation.
"""

import re
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.rag.vector_store import PersistentVectorStore

# Telecom domain keywords mapped to tables and concepts for lexical boosting
KEYWORD_TABLE_BOOSTS = {
    "prepaid": ["subscriber_profile", "churn_events"],
    "postpaid": ["subscriber_profile", "usage_daily"],
    "loss": ["churn_events", "subscriber_profile"],
    "churn": ["churn_events", "subscriber_profile"],
    "churned": ["churn_events", "subscriber_profile"],
    "west": ["subscriber_profile"],
    "western": ["subscriber_profile"],
    "region": ["subscriber_profile"],
    "ramadan": ["campaign_response"],
    "campaign": ["campaign_response"],
    "response": ["campaign_response"],
    "small business": ["subscriber_profile", "usage_daily"],
    "drop": ["usage_daily"],
    "decline": ["usage_daily"],
    "usage": ["usage_daily"],
    "data": ["usage_daily", "campaign_response"],
    "mb": ["usage_daily"],
    "minutes": ["usage_daily"],
    "revenue": ["revenue_monthly"],
    "billed": ["revenue_monthly"],
    "collected": ["revenue_monthly"],
    "early": ["churn_events", "subscriber_profile"],
    "channel": ["churn_events"],
    "quarter": ["churn_events", "revenue_monthly"],
}


class GroundedContextPackage:
    """Encapsulates retrieved and formatted knowledge for the prompt."""

    def __init__(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        schema_context: str,
        glossary_context: str,
        rules_context: str,
        examples_context: str,
        top_tables: List[str],
    ):
        self.question = question
        self.chunks = chunks
        self.schema_context = schema_context
        self.glossary_context = glossary_context
        self.rules_context = rules_context
        self.examples_context = examples_context
        self.top_tables = top_tables

    def get_full_prompt_context(self) -> str:
        """Assembles structured prompt text bounded for fast local inference."""
        sections = []

        if self.schema_context:
            schema_text = self.schema_context[:1200]
            sections.append(f"### 1. RELEVANT DATABASE SCHEMA & RELATIONSHIPS\n{schema_text}")

        if self.glossary_context:
            glossary_text = self.glossary_context[:800]
            sections.append(f"### 2. BUSINESS DEFINITIONS & CALCULATION RULES\n{glossary_text}")

        if self.rules_context:
            rules_text = self.rules_context[:800]
            sections.append(f"### 3. GOVERNING ANALYTICAL RULES\n{rules_text}")

        if self.examples_context:
            # Take only the top few-shot example for immediate grounding
            example_parts = self.examples_context.split("\n\n---\n\n")
            top_example = example_parts[0] if example_parts else self.examples_context
            sections.append(f"### 4. VALIDATED SQL EXAMPLE (PRIMARY GROUNDING)\n{top_example[:1000]}")

        return "\n\n".join(sections)


class KnowledgeRetriever:
    """Coordinates hybrid retrieval from persistent vector store."""

    def __init__(self, vector_store: Optional[PersistentVectorStore] = None):
        self.store = vector_store or PersistentVectorStore()

    def retrieve(self, question: str, top_k: int = None) -> GroundedContextPackage:
        """
        Executes hybrid retrieval:
        1. Semantic vector search.
        2. Keyword/table lexical boost.
        3. Re-ranks and deduplicates.
        4. Partitions into schema, glossary, rules, and validated examples.
        """
        k = top_k or settings.RAG_TOP_K
        raw_hits = self.store.search(question, top_k=k * 2)

        # Apply lexical score boost based on keyword matching
        q_lower = question.lower()
        scored_hits = []

        for hit in raw_hits:
            score = hit["similarity"]
            content_lower = hit["content"].lower()
            doc_table = hit.get("table", "").lower()

            # Boost if domain keyword matches table or content
            for kw, target_tables in KEYWORD_TABLE_BOOSTS.items():
                if kw in q_lower:
                    if any(t in doc_table for t in target_tables):
                        score += 0.20
                    if kw in content_lower:
                        score += 0.10

            # Boost validated examples that match key intent
            if hit["source_type"] == "example":
                ex_q = hit.get("metadata", {}).get("question", "").lower()
                # Check token overlap
                q_words = set(re.findall(r"\w+", q_lower))
                ex_words = set(re.findall(r"\w+", ex_q))
                overlap = len(q_words.intersection(ex_words))
                if overlap >= 3:
                    score += 0.35

            # Always ensure relationships schema chunk is present if multiple tables detected
            if "relationships" in doc_table:
                score += 0.15

            hit["final_score"] = round(score, 4)
            scored_hits.append(hit)

        # Sort by final score
        scored_hits.sort(key=lambda x: x["final_score"], reverse=True)

        # Select top chunks while maintaining diverse representation
        selected_chunks = []
        seen_ids = set()
        categories_count = {}

        for hit in scored_hits:
            doc_id = hit["doc_id"]
            if doc_id in seen_ids:
                continue
            st = hit["source_type"]
            # Limit per source type to avoid monopolization
            if categories_count.get(st, 0) >= 3 and len(selected_chunks) < k:
                continue

            seen_ids.add(doc_id)
            selected_chunks.append(hit)
            categories_count[st] = categories_count.get(st, 0) + 1

            if len(selected_chunks) >= k:
                break

        # Partition into categorized contexts
        schema_parts = []
        glossary_parts = []
        rules_parts = []
        examples_parts = []
        tables_identified = set()

        for chunk in selected_chunks:
            st = chunk["source_type"]
            c_text = chunk["content"]
            tbl = chunk.get("table", "")
            if tbl and tbl not in ["general", "all"]:
                for t in tbl.split(","):
                    t_clean = t.strip()
                    if t_clean:
                        tables_identified.add(t_clean)

            if st == "schema":
                schema_parts.append(c_text)
            elif st == "glossary":
                glossary_parts.append(c_text)
            elif st == "business_rule":
                rules_parts.append(c_text)
            elif st == "example":
                examples_parts.append(c_text)

        return GroundedContextPackage(
            question=question,
            chunks=selected_chunks,
            schema_context="\n\n---\n\n".join(schema_parts),
            glossary_context="\n\n---\n\n".join(glossary_parts),
            rules_context="\n\n---\n\n".join(rules_parts),
            examples_context="\n\n---\n\n".join(examples_parts),
            top_tables=sorted(list(tables_identified)),
        )
