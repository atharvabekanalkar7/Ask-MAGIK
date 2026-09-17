"""
Knowledge Document Loader & Chunker
Ask MAGIK - Phase 2 RAG Engine

Dynamically reads existing knowledge files:
- backend/knowledge/schema/*.md
- backend/knowledge/glossary/glossary.md
- backend/knowledge/business_rules/business_rules.md
- backend/knowledge/examples/validated_examples.json

Normalizes documents and generates chunks with rich metadata.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from backend.config import BASE_DIR

KNOWLEDGE_DIR = BASE_DIR / "backend" / "knowledge"


class KnowledgeDocument:
    """Represents a single indexed knowledge chunk with metadata."""

    def __init__(
        self,
        doc_id: str,
        content: str,
        source_type: str,
        table: str,
        document_name: str,
        category: str,
        metadata: Dict[str, Any] = None,
    ):
        self.doc_id = doc_id
        self.content = content.strip()
        self.source_type = source_type
        self.table = table
        self.document_name = document_name
        self.category = category
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "source_type": self.source_type,
            "table": self.table,
            "document_name": self.document_name,
            "category": self.category,
            "metadata": self.metadata,
        }


def load_schema_documents() -> List[KnowledgeDocument]:
    """Loads all schema documentation files and chunks them appropriately."""
    schema_dir = KNOWLEDGE_DIR / "schema"
    if not schema_dir.exists():
        return []

    docs = []
    for md_file in schema_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        table_name = md_file.stem

        if table_name == "relationships":
            # Split relationships by section
            sections = re.split(r"\n(?=##\s+)", content)
            for idx, sec in enumerate(sections):
                sec = sec.strip()
                if not sec:
                    continue
                doc_id = f"schema_rel_{idx}"
                docs.append(
                    KnowledgeDocument(
                        doc_id=doc_id,
                        content=sec,
                        source_type="schema",
                        table="relationships",
                        document_name=md_file.name,
                        category="relationships",
                        metadata={"title": "DataMart Relationships & Valid Joins"},
                    )
                )
        else:
            # Per-table schema doc
            # Chunk into overview/columns and analytical use cases if long
            doc_id = f"schema_table_{table_name}"
            docs.append(
                KnowledgeDocument(
                    doc_id=doc_id,
                    content=content,
                    source_type="schema",
                    table=table_name,
                    document_name=md_file.name,
                    category="table_schema",
                    metadata={"table_name": table_name},
                )
            )

    return docs


def load_glossary_documents() -> List[KnowledgeDocument]:
    """Loads glossary terms, creating a chunk for each term definition."""
    glossary_file = KNOWLEDGE_DIR / "glossary" / "glossary.md"
    if not glossary_file.exists():
        return []

    content = glossary_file.read_text(encoding="utf-8")
    # Split by term header: ## 1. Term Name or ## Term Name
    term_blocks = re.split(r"\n(?=##\s+)", content)
    docs = []

    for idx, block in enumerate(term_blocks):
        block = block.strip()
        if not block or block.startswith("# Skyline Telecom Business Glossary"):
            continue

        # Extract term title
        first_line = block.split("\n")[0]
        term_name = re.sub(r"^##\s+(\d+\.\s+)?", "", first_line).strip()

        # Infer associated table from block text if present
        table_match = re.search(r"Primary table[s]?\s*:\s*`?([a-zA-Z0-9_]+)`?", block, re.IGNORECASE)
        table = table_match.group(1) if table_match else "general"

        doc_id = f"glossary_{re.sub(r'[^a-zA-Z0-9_]', '_', term_name.lower())}_{idx}"
        docs.append(
            KnowledgeDocument(
                doc_id=doc_id,
                content=block,
                source_type="glossary",
                table=table,
                document_name="glossary.md",
                category="business_glossary",
                metadata={"term": term_name},
            )
        )

    return docs


def load_business_rules_documents() -> List[KnowledgeDocument]:
    """Loads business rules and chunks by rule group."""
    rules_file = KNOWLEDGE_DIR / "business_rules" / "business_rules.md"
    if not rules_file.exists():
        return []

    content = rules_file.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=##\s+)", content)
    docs = []

    for idx, sec in enumerate(sections):
        sec = sec.strip()
        if not sec or sec.startswith("# Skyline Telecom Business"):
            continue

        first_line = sec.split("\n")[0]
        rule_group = re.sub(r"^##\s+(\d+\.\s+)?", "", first_line).strip()

        doc_id = f"business_rule_{idx}"
        docs.append(
            KnowledgeDocument(
                doc_id=doc_id,
                content=sec,
                source_type="business_rule",
                table="all",
                document_name="business_rules.md",
                category="business_rules",
                metadata={"rule_group": rule_group},
            )
        )

    return docs


def load_validated_examples_documents() -> List[KnowledgeDocument]:
    """Loads validated question-SQL examples."""
    examples_file = KNOWLEDGE_DIR / "examples" / "validated_examples.json"
    if not examples_file.exists():
        return []

    with open(examples_file, "r", encoding="utf-8") as f:
        examples = json.load(f)

    docs = []
    for ex in examples:
        ex_id = ex.get("id", "ex")
        question = ex.get("question", "")
        intent = ex.get("intent", "")
        tables = ex.get("tables", [])
        sql = ex.get("sql", "")
        explanation = ex.get("explanation", "")
        rules = ex.get("business_rules", [])

        content = (
            f"Question: {question}\n"
            f"Intent: {intent}\n"
            f"Target Tables: {', '.join(tables)}\n"
            f"Applied Rules: {' | '.join(rules)}\n"
            f"SQL:\n{sql}\n"
            f"Explanation: {explanation}"
        )

        doc_id = f"example_{ex_id.lower()}"
        docs.append(
            KnowledgeDocument(
                doc_id=doc_id,
                content=content,
                source_type="example",
                table=",".join(tables),
                document_name="validated_examples.json",
                category="few_shot_example",
                metadata={
                    "example_id": ex_id,
                    "question": question,
                    "sql": sql,
                    "tables": tables,
                },
            )
        )

    return docs


def load_all_knowledge_documents() -> List[KnowledgeDocument]:
    """Loads all knowledge sources and returns consolidated list of KnowledgeDocuments."""
    all_docs = []
    all_docs.extend(load_schema_documents())
    all_docs.extend(load_glossary_documents())
    all_docs.extend(load_business_rules_documents())
    all_docs.extend(load_validated_examples_documents())
    return all_docs
