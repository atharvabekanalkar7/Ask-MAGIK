"""
Transparent Confidence Scoring Engine
Ask MAGIK - Phase 2 Local AI Engine

Calculates query confidence from observable operational signals:
- RAG retrieval relevance score
- SQL firewall validation pass
- Presence of matching validated examples
- Execution result non-emptiness & anomaly audits
- Ambiguity and assumption density
"""

from typing import List, Dict, Any, Tuple
from backend.services.sql_validator import SQLValidationResult
from backend.services.result_validator import ResultAudit
from backend.rag.retriever import GroundedContextPackage


class ConfidenceAssessment:
    """Confidence level, numeric score, and transparent reasons."""

    def __init__(self, level: str, score: float, reasons: List[str]):
        self.level = level  # 'HIGH', 'MEDIUM', 'LOW', 'NEEDS_CLARIFICATION'
        self.score = round(score, 2)
        self.reasons = reasons

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "reasons": self.reasons,
        }


class ConfidenceScorer:
    """Evaluates multi-signal confidence."""

    def evaluate(
        self,
        context_package: GroundedContextPackage,
        sql_validation: SQLValidationResult,
        result_audit: ResultAudit,
        ambiguity_detected: bool,
        clarification_needed: bool,
        assumptions: List[str],
    ) -> ConfidenceAssessment:
        reasons = []
        score = 0.0

        if clarification_needed:
            return ConfidenceAssessment(
                level="NEEDS_CLARIFICATION",
                score=0.20,
                reasons=["Analytical ambiguity detected requiring user clarification."],
            )

        # 1. SQL Firewall signal (30 pts)
        if sql_validation.is_valid:
            score += 0.30
            reasons.append("SQL query passed all Query Firewall security and schema checks.")
        else:
            reasons.append("SQL query failed firewall checks.")

        # 2. RAG Retrieval signal (25 pts)
        has_example = any(c.get("source_type") == "example" for c in context_package.chunks)
        if has_example:
            score += 0.25
            reasons.append("Strong semantic match found in Validated Golden SQL Examples.")
        elif len(context_package.chunks) >= 3:
            score += 0.15
            reasons.append("Retrieved relevant schema and business rule context.")
        else:
            reasons.append("Sparse RAG retrieval context.")

        # 3. Result Validity signal (25 pts)
        if result_audit.is_valid and not result_audit.stats.get("empty_result", False):
            score += 0.25
            reasons.append(f"Query returned valid non-empty results ({result_audit.stats.get('row_count', 0)} rows).")
        elif result_audit.stats.get("empty_result", False):
            score += 0.10
            reasons.append("Query returned zero rows (valid SQL, but no records matched filters).")
        else:
            reasons.append(f"Result audit raised warnings: {'; '.join(result_audit.warnings)}.")

        # 4. Ambiguity & Assumptions signal (20 pts)
        if not ambiguity_detected and len(assumptions) <= 2:
            score += 0.20
            reasons.append("Zero semantic ambiguity detected in question.")
        elif ambiguity_detected:
            score += 0.05
            reasons.append(f"Question contained minor ambiguities resolved via explicit assumptions: {assumptions}.")
        else:
            score += 0.10
            reasons.append(f"Standard assumptions applied: {len(assumptions)}.")

        # Determine level band
        if score >= 0.80:
            level = "HIGH"
        elif score >= 0.60:
            level = "MEDIUM"
        else:
            level = "LOW"

        return ConfidenceAssessment(level=level, score=score, reasons=reasons)
