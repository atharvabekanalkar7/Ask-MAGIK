"""
Safe Database Query Executor
Ask MAGIK - Phase 2 Local AI Engine

Executes validated, sanitized read-only SQL queries against skyline.db.
Enforces execution time measurement, column extraction, and row limits.
"""

import time
import sqlite3
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from backend.config import settings
from backend.database.connection import engine
from backend.services.sql_validator import SQLFirewall, SQLValidationResult


class ExecutionResult:
    """Encapsulates SQL query execution results."""

    def __init__(
        self,
        success: bool,
        columns: List[str],
        rows: List[List[Any]],
        row_count: int,
        execution_time_ms: float,
        sql_executed: str,
        error_message: Optional[str] = None,
        validation: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.columns = columns
        self.rows = rows
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.sql_executed = sql_executed
        self.error_message = error_message
        self.validation = validation or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "sql_executed": self.sql_executed,
            "error_message": self.error_message,
            "validation": self.validation,
        }


class SafeQueryExecutor:
    """Coordinates validation and read-only execution against the database."""

    def __init__(self, firewall: Optional[SQLFirewall] = None):
        self.firewall = firewall or SQLFirewall()

    def execute(self, raw_sql: str) -> ExecutionResult:
        """
        1. Validates SQL through Query Firewall.
        2. Executes query inside read-only connection.
        3. Formats results and measures runtime.
        """
        # Step 1: Firewall validation
        validation: SQLValidationResult = self.firewall.validate_and_sanitize(raw_sql)
        if not validation.is_valid:
            return ExecutionResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=0.0,
                sql_executed=raw_sql,
                error_message=f"Query rejected by SQL Firewall: {'; '.join(validation.errors)}",
                validation=validation.to_dict(),
            )

        sanitized_sql = validation.sanitized_sql
        start_time = time.perf_counter()

        # Step 2: Database execution
        try:
            with engine.connect() as conn:
                # Enforce read-only pragma if SQLite
                if settings.is_sqlite:
                    conn.execute(text("PRAGMA query_only = ON;"))

                cursor_result = conn.execute(text(sanitized_sql))
                columns = list(cursor_result.keys()) if cursor_result.returns_rows else []
                raw_rows = cursor_result.fetchall() if cursor_result.returns_rows else []

                # Convert tuples/Row objects into standard serializable lists
                serializable_rows = []
                for r in raw_rows:
                    row_vals = []
                    for v in r:
                        if hasattr(v, "isoformat"):
                            row_vals.append(v.isoformat())
                        else:
                            row_vals.append(v)
                    serializable_rows.append(row_vals)

                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return ExecutionResult(
                    success=True,
                    columns=columns,
                    rows=serializable_rows,
                    row_count=len(serializable_rows),
                    execution_time_ms=elapsed_ms,
                    sql_executed=sanitized_sql,
                    validation=validation.to_dict(),
                )

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ExecutionResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
                sql_executed=sanitized_sql,
                error_message=f"SQL execution error: {str(e)}",
                validation=validation.to_dict(),
            )
