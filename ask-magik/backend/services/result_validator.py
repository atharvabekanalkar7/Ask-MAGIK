"""
Result Validator
Ask MAGIK - Phase 2 Local AI Engine

Audits database query execution outputs for anomalies, null concentrations,
negative figures, and boundary violations without silently altering data.
"""

from typing import List, Dict, Any


class ResultAudit:
    """Findings from auditing query results."""

    def __init__(self, is_valid: bool, warnings: List[str], stats: Dict[str, Any]):
        self.is_valid = is_valid
        self.warnings = warnings
        self.stats = stats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "warnings": self.warnings,
            "stats": self.stats,
        }


class ResultValidator:
    """Validates returned SQL rows against business sanity rules."""

    def validate(self, columns: List[str], rows: List[List[Any]]) -> ResultAudit:
        warnings = []
        row_count = len(rows)
        stats = {
            "row_count": row_count,
            "column_count": len(columns),
            "empty_result": row_count == 0,
        }

        # 1. Empty set check
        if row_count == 0:
            warnings.append("Query returned zero rows. Criteria may be overly restrictive or dates out of range.")
            return ResultAudit(is_valid=True, warnings=warnings, stats=stats)

        # 2. Check for all-NULL columns
        col_null_counts = [0] * len(columns)
        for row in rows:
            for idx, val in enumerate(row):
                if val is None:
                    col_null_counts[idx] += 1

        for idx, null_cnt in enumerate(col_null_counts):
            if null_cnt == row_count:
                warnings.append(f"Column '{columns[idx]}' contains 100% NULL values.")

        # 3. Check for negative numbers on non-negative metrics
        non_negative_keywords = ["revenue", "billed", "collected", "data", "minutes", "sms", "count", "loss", "churn"]
        for c_idx, col_name in enumerate(columns):
            col_lower = col_name.lower()
            if any(kw in col_lower for kw in non_negative_keywords):
                for r_idx, row in enumerate(rows):
                    val = row[c_idx]
                    if isinstance(val, (int, float)) and val < 0:
                        warnings.append(f"Negative value ({val}) detected in non-negative metric column '{col_name}'.")
                        break

        # 4. Check for invalid percentages (> 100 or < 0)
        pct_keywords = ["pct", "percent", "rate"]
        for c_idx, col_name in enumerate(columns):
            col_lower = col_name.lower()
            if any(kw in col_lower for kw in pct_keywords):
                for row in rows:
                    val = row[c_idx]
                    if isinstance(val, (int, float)):
                        if val > 100.0 or val < 0.0:
                            warnings.append(f"Unusual percentage ({val}%) detected in column '{col_name}'.")
                            break

        return ResultAudit(
            is_valid=len(warnings) == 0,
            warnings=warnings,
            stats=stats,
        )
