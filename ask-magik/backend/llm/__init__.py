"""
LLM Package for Ask MAGIK
Provides Ollama integration, prompt engineering, and structured generation schemas.
"""

from .ollama_client import OllamaClient
from .schemas import SQLGenerationResult, AnswerExplanationResult
from .prompts import SQL_SYSTEM_PROMPT, EXPLANATION_SYSTEM_PROMPT

__all__ = [
    "OllamaClient",
    "SQLGenerationResult",
    "AnswerExplanationResult",
    "SQL_SYSTEM_PROMPT",
    "EXPLANATION_SYSTEM_PROMPT",
]
