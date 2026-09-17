"""
Pydantic Schemas for LLM Communication
Ask MAGIK - Phase 2 Local AI Engine
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SQLGenerationResult(BaseModel):
    """Structured response from LLM for SQL translation."""

    question_understanding: str = Field(
        ...,
        description="Concise description of the analytical task extracted from the user question."
    )
    tables_needed: List[str] = Field(
        default_factory=list,
        description="List of table names required to fulfill the query."
    )
    sql: str = Field(
        ...,
        description="The generated SQLite-compatible SELECT query."
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Explicit assumptions made regarding date ranges, metrics, or definitions."
    )
    ambiguity_detected: bool = Field(
        default=False,
        description="True if the question lacks essential parameters or has conflicting meanings."
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if the query cannot be responsibly generated without user clarification."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Specific question to ask the user if clarification is needed."
    )


class AnswerExplanationResult(BaseModel):
    """Structured natural language explanation of executed query results."""

    answer: str = Field(
        ...,
        description="Concise, plain-English executive summary answering the question directly."
    )
    key_insight: str = Field(
        ...,
        description="Strategic takeaway, pattern, or anomaly discovered in the data."
    )
    supporting_figures: List[str] = Field(
        default_factory=list,
        description="Exact data values cited directly from the query execution results."
    )
    caveats: List[str] = Field(
        default_factory=list,
        description="Assumptions, scope limitations, or freshness caveats."
    )
