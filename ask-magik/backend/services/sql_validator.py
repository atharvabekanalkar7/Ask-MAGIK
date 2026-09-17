"""
SQL Validator & Query Firewall
Ask MAGIK - Phase 2 Local AI Engine

Performs multi-layer security and integrity checks before execution:
1. Rejects multi-statement execution.
2. Enforces read-only SELECT policy (strictly blocks INSERT, UPDATE, DELETE, DROP, etc.).
3. Enforces strict table allowlist against DataMart schema.
4. Detects suspicious patterns and SQL injection attempts.
5. Injects safe row limits when appropriate.
"""

import re
from typing import List, Set, Dict, Any, Tuple, Optional
from backend.config import settings

ALLOWED_TABLES: Set[str] = {
    "subscriber_profile",
    "usage_daily",
    "campaign_response",
    "revenue_monthly",
    "churn_events",
}

DISALLOWED_COMMANDS: List[str] = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
]


class SQLValidationResult:
    """Result returned by SQL Validator."""

    def __init__(
        self,
        is_valid: bool,
        sanitized_sql: str,
        tables_used: List[str],
        errors: List[str],
        warnings: List[str],
    ):
        self.is_valid = is_valid
        self.sanitized_sql = sanitized_sql
        self.tables_used = tables_used
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "sanitized_sql": self.sanitized_sql,
            "tables_used": self.tables_used,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class SQLFirewall:
    """Read-only security firewall for Text-to-SQL execution."""

    def __init__(self, allowed_tables: Optional[Set[str]] = None, max_rows: int = None):
        self.allowed_tables = allowed_tables or ALLOWED_TABLES
        self.max_rows = max_rows or settings.SQL_MAX_ROWS

    def validate_and_sanitize(self, raw_sql: str) -> SQLValidationResult:
        """
        Validates the SQL statement against strict security rules.
        Returns SQLValidationResult.
        """
        errors = []
        warnings = []
        sql = raw_sql.strip()

        # Clean markdown wrappers if present
        if sql.startswith("```"):
            sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
            sql = re.sub(r"\s*```$", "", sql)
            sql = sql.strip()

        if not sql:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql="",
                tables_used=[],
                errors=["Empty SQL statement provided."],
                warnings=[],
            )

        # 1. Multi-statement check
        # Remove comments first
        clean_text = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        clean_text = re.sub(r"/\*.*?\*/", "", clean_text, flags=re.DOTALL).strip()

        # Split by semicolon
        statements = [s.strip() for s in clean_text.split(";") if s.strip()]
        if len(statements) > 1:
            errors.append(f"Multiple SQL statements detected ({len(statements)}). Only single queries are allowed.")
            return SQLValidationResult(False, sql, [], errors, warnings)

        single_query = statements[0] if statements else ""

        # 2. Strict SELECT enforcement
        # Must start with SELECT or WITH (for CTEs)
        match_start = re.match(r"^(SELECT|WITH)\b", single_query, re.IGNORECASE)
        if not match_start:
            errors.append("Statement must begin with SELECT or WITH (read-only queries only).")

        # 3. Disallowed mutation tokens
        for kw in DISALLOWED_COMMANDS:
            # Word boundary regex check
            if re.search(rf"\b{kw}\b", single_query, re.IGNORECASE):
                errors.append(f"Disallowed mutating SQL command detected: '{kw}'.")

        # 4. Extract and validate tables
        tables_used, cte_names = self._extract_tables_and_ctes(single_query)
        if not tables_used:
            errors.append("No valid database tables detected in the query.")

        disallowed_tables = []
        for tbl in tables_used:
            if tbl.lower() not in self.allowed_tables and tbl.lower() not in cte_names:
                disallowed_tables.append(tbl)

        if disallowed_tables:
            errors.append(
                f"Disallowed or unknown tables referenced: {disallowed_tables}. "
                f"Permitted tables: {sorted(list(self.allowed_tables))}."
            )

        # 5. Invalidate if errors found
        if errors:
            return SQLValidationResult(False, single_query, tables_used, errors, warnings)

        # 6. Apply safe LIMIT if detail query lacking LIMIT
        sanitized_sql = self._apply_safe_limit(single_query)

        # Ensure single trailing semicolon
        if not sanitized_sql.endswith(";"):
            sanitized_sql += ";"

        return SQLValidationResult(
            is_valid=True,
            sanitized_sql=sanitized_sql,
            tables_used=tables_used,
            errors=[],
            warnings=warnings,
        )

    def _extract_tables_and_ctes(self, sql: str) -> Tuple[List[str], Set[str]]:
        """Extracts table references and identifies CTE aliases."""
        cte_names = set()
        # Find CTE names: WITH name AS (...)
        cte_matches = re.findall(r"\b(?:WITH|,)\s*([a-zA-Z0-9_]+)\s+AS\s*\(", sql, re.IGNORECASE)
        for c in cte_matches:
            cte_names.add(c.lower())

        # Extract FROM and JOIN targets
        from_matches = re.findall(r"\bFROM\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)
        join_matches = re.findall(r"\bJOIN\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)

        raw_tables = set(from_matches + join_matches)
        actual_tables = [t for t in raw_tables if t.lower() not in cte_names]

        # Also check for direct mention of allowed tables in case of complex subqueries
        for allowed in self.allowed_tables:
            if re.search(rf"\b{allowed}\b", sql, re.IGNORECASE) and allowed not in actual_tables:
                actual_tables.append(allowed)

        return sorted(list(set(actual_tables))), cte_names

    def _apply_safe_limit(self, sql: str) -> str:
        """Injects LIMIT if the query is a SELECT without aggregation or explicit limit."""
        has_limit = bool(re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE))
        has_agg = bool(re.search(r"\b(COUNT|SUM|AVG|MIN|MAX|GROUP\s+BY)\b", sql, re.IGNORECASE))

        # If it's a raw SELECT * without LIMIT or GROUP BY, apply max_rows guard
        if not has_limit and not has_agg:
            return f"{sql.rstrip(';')} LIMIT {self.max_rows}"

        return sql
