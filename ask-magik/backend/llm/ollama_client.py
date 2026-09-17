"""
Ollama Local LLM Client
Ask MAGIK - Phase 2 Local AI Engine

Interfaces with local Ollama daemon (default: http://localhost:11434).
Uses httpx for high-performance async/sync communication without heavy dependencies.
Provides structured JSON generation, model detection, and offline error handling.
"""

import json
import re
from typing import List, Dict, Any, Optional
import httpx
from backend.config import settings
from backend.llm.schemas import SQLGenerationResult, AnswerExplanationResult
from backend.llm.prompts import (
    SQL_SYSTEM_PROMPT,
    build_sql_prompt,
    EXPLANATION_SYSTEM_PROMPT,
    build_explanation_prompt,
)


class OllamaClient:
    """Client for local Ollama instance."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        raw_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.base_url = raw_url.replace("localhost", "127.0.0.1")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.timeout = timeout_seconds if timeout_seconds is not None else settings.LLM_TIMEOUT_SECONDS
        self._cached_available: Optional[bool] = None
        self._last_available_check: float = 0.0

    def is_available(self) -> bool:
        """Checks if the Ollama daemon is reachable (cached for 10s)."""
        import time
        now = time.time()
        if self._cached_available is not None and (now - self._last_available_check) < 10.0:
            return self._cached_available

        try:
            with httpx.Client(timeout=0.3) as client:
                res = client.get(f"{self.base_url}/api/tags")
                self._cached_available = (res.status_code == 200)
        except Exception:
            self._cached_available = False

        self._last_available_check = now
        return self._cached_available

    def get_installed_models(self) -> List[str]:
        """Returns list of model names currently pulled in Ollama."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    return [m.get("name", "") for m in models]
        except Exception:
            pass
        return []

    def get_active_model(self) -> str:
        """
        Selects best available model:
        1. Configured model (if installed)
        2. Any installed llama model (e.g. llama3, llama3.2)
        3. Any other installed model (e.g. phi3, gemma3)
        4. Fallback to configured model name
        """
        installed = self.get_installed_models()
        if not installed:
            return self.model_name

        if self.model_name in installed:
            return self.model_name

        # Look for llama models
        for m in installed:
            if "llama" in m.lower():
                return m

        # Look for phi or gemma
        for m in installed:
            if "phi3" in m.lower() or "gemma" in m.lower():
                return m

        return installed[0]

    def generate_structured_sql(
        self,
        question: str,
        context_package_text: str,
        model_override: Optional[str] = None,
    ) -> SQLGenerationResult:
        """
        Calls Ollama to generate structured SQL grounded in retrieved knowledge.
        Returns parsed Pydantic SQLGenerationResult.
        """
        if not self.is_available():
            raise ConnectionError(
                f"Local Ollama engine unavailable at {self.base_url}. "
                "Ensure Ollama is running and your model is installed (e.g. 'ollama run llama3')."
            )

        active_model = model_override or self.get_active_model()
        user_prompt = build_sql_prompt(question, context_package_text)

        payload = {
            "model": active_model,
            "prompt": user_prompt,
            "system": SQL_SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "top_p": 0.9,
                "num_predict": 220,
                "num_ctx": 2048,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                raw_response = response.json().get("response", "").strip()

            parsed_json = self._extract_json(raw_response)
            return SQLGenerationResult(**parsed_json)

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API HTTP error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            # If JSON parsing or validation fails, attempt recovery
            return self._attempt_sql_recovery(raw_response if 'raw_response' in locals() else "", question, str(e))

    def generate_explanation(
        self,
        question: str,
        sql: str,
        columns: List[str],
        rows: List[Any],
        assumptions: List[str],
        model_override: Optional[str] = None,
    ) -> AnswerExplanationResult:
        """
        Calls Ollama to generate natural language explanation of executed results.
        """
        if not self.is_available():
            # Graceful summary if Ollama is unreachable
            return self._generate_heuristic_explanation(question, columns, rows)

        active_model = model_override or self.get_active_model()
        user_prompt = build_explanation_prompt(question, sql, columns, rows, assumptions)

        payload = {
            "model": active_model,
            "prompt": user_prompt,
            "system": EXPLANATION_SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 180,
                "num_ctx": 2048,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                raw_response = response.json().get("response", "").strip()

            parsed_json = self._extract_json(raw_response)
            return AnswerExplanationResult(**parsed_json)

        except Exception:
            return self._generate_heuristic_explanation(question, columns, rows)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extracts and parses JSON object from LLM response text."""
        text = text.strip()
        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Regex search for JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError(f"Failed to parse JSON from model output: {text[:200]}...")

    def _attempt_sql_recovery(self, raw_text: str, question: str, error_msg: str) -> SQLGenerationResult:
        """Recovers SQL if output was wrapped or partially malformed."""
        sql_match = re.search(r"SELECT\s+.*?;", raw_text, re.IGNORECASE | re.DOTALL)
        if sql_match:
            sql = sql_match.group(0).strip()
            return SQLGenerationResult(
                question_understanding=f"Extracted query for: {question}",
                tables_needed=["subscriber_profile"],
                sql=sql,
                assumptions=["Recovered from unformatted output"],
                ambiguity_detected=False,
                clarification_needed=False,
            )
        raise ValueError(f"Could not parse valid SQL from model output: {error_msg}")

    def _generate_heuristic_explanation(
        self,
        question: str,
        columns: List[str],
        rows: List[Any],
    ) -> AnswerExplanationResult:
        """Deterministic data-grounded explanation when LLM explanation is skipped."""
        if not rows:
            return AnswerExplanationResult(
                answer="No matching records were found in the database for the specified criteria.",
                key_insight="Zero records returned from the query execution.",
                supporting_figures=["0 rows returned"],
                caveats=["Check date filters or dimension values."],
            )

        row_count = len(rows)
        first_row = rows[0]
        figures = []
        if isinstance(first_row, (list, tuple)):
            for col, val in zip(columns, first_row):
                figures.append(f"{col}: {val}")
        elif isinstance(first_row, dict):
            for col, val in first_row.items():
                figures.append(f"{col}: {val}")

        return AnswerExplanationResult(
            answer=f"Analysis of {row_count} records indicates top metric: {', '.join(figures[:2])}.",
            key_insight=f"Primary concentration observed in top row ({', '.join(figures[:2])}).",
            supporting_figures=figures[:4],
            caveats=["Underlying data refreshed once daily."],
        )
