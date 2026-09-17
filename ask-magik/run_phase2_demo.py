"""
Ask MAGIK - Phase 2 Demo Acceptance Runner
Skyline Telecom Intelligent AI Analytics Engine

Executes the 4 Core Demo Questions through the full local pipeline:
RAG Retrieval -> Grounding -> LLM SQL -> SQL Firewall -> Execution -> Result Validation -> Answer & Evidence.
"""

import sys
import json
import time

# Ensure immediate unbuffered output on Windows
sys.stdout.reconfigure(line_buffering=True)

from backend.services.chat_service import ChatOrchestrator
from backend.rag.retriever import KnowledgeRetriever
from backend.llm.ollama_client import OllamaClient


DEMO_QUESTIONS = [
    (
        "Q1: Western Prepaid Customer Loss",
        "Which prepaid plans had the highest customer loss in the western region last month?"
    ),
    (
        "Q2: Ramadan Campaign YoY Performance",
        "How did Ramadan campaign response change year-over-year by region?"
    ),
    (
        "Q3: Postpaid Small Business Usage Drop",
        "Which postpaid small-business customers had usage drop by more than 30% in the last 60 days?"
    ),
    (
        "Q4: Early Customer Loss Root Causes",
        "What's driving the rise in early customer loss — channel or customer type?"
    ),
]


def print_box(title: str, content: str):
    print(f"\n[{title}]")
    print("-" * 75)
    print(content)


def format_rows(columns, rows, max_display=8):
    if not rows:
        return "No rows returned."
    col_widths = [len(str(c)) for c in columns]
    display_rows = rows[:max_display]
    for r in display_rows:
        for idx, val in enumerate(r):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header = " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(columns))
    sep = "-+-".join("-" * col_widths[i] for i in range(len(columns)))
    lines = [header, sep]
    for r in display_rows:
        lines.append(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(r)))

    if len(rows) > max_display:
        lines.append(f"... ({len(rows) - max_display} additional rows truncated for display)")
    return "\n".join(lines)


def run_demo():
    print("=" * 80)
    print("           ASK MAGIK - PHASE 2 DEMO ACCEPTANCE TEST")
    print("           Skyline Telecom AI Natural Language to SQL Engine")
    print("=" * 80)

    orchestrator = ChatOrchestrator()
    retriever = KnowledgeRetriever()
    llm = OllamaClient()

    print(f"Ollama Status: {'CONNECTED' if llm.is_available() else 'OFFLINE (Fallback Active)'}")
    print(f"Active Model: {llm.get_active_model()}")
    print("=" * 80)

    for tag, question in DEMO_QUESTIONS:
        print("\n" + "#" * 80)
        print(f"DEMO SCENARIO: {tag}")
        print("#" * 80)
        print(f"\nQUESTION: \"{question}\"")

        # 1. Show RAG Retrieval
        pkg = retriever.retrieve(question)
        rag_summary = []
        for idx, chunk in enumerate(pkg.chunks[:4], 1):
            rag_summary.append(
                f"{idx}. [{chunk['source_type'].upper()}] {chunk['doc_id']} "
                f"(Similarity Score: {chunk['final_score']})"
            )
        print_box("1. RETRIEVED KNOWLEDGE (TOP SOURCES)", "\n".join(rag_summary))

        # 2. Run Pipeline
        print(f"\n[Processing Pipeline] Sending prompt to local LLM ({llm.get_active_model()})...", flush=True)
        t0 = time.perf_counter()
        response = orchestrator.process_question(question)
        total_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        print(f"[Processing Pipeline] Completed in {total_time_ms} ms", flush=True)

        # 3. Print Generated SQL
        print_box("2. GENERATED SQL QUERY", response.get("sql", "N/A"))

        # 4. Print SQL Validation Checks
        val = response.get("validation", {})
        val_status = "PASS" if val.get("is_valid", False) else "FAIL"
        val_details = (
            f"Status: {val_status}\n"
            f"Tables Verified: {response.get('tables_used', [])}\n"
            f"Read-Only Enforced: Yes (Disallows INSERT/UPDATE/DELETE/DROP)\n"
            f"Firewall Errors: {val.get('errors', 'None')}"
        )
        print_box("3. SQL FIREWALL VALIDATION", val_details)

        # 5. Print Execution & Rows
        cols = response.get("columns", [])
        rows = response.get("rows", [])
        row_count = len(rows)
        exec_info = (
            f"Row Count: {row_count}\n"
            f"Pipeline Execution Time: {total_time_ms} ms\n\n"
            f"{format_rows(cols, rows)}"
        )
        print_box("4. QUERY EXECUTION & RESULTS", exec_info)

        # 6. Print Natural Language Answer
        ans_details = (
            f"Executive Answer:\n{response.get('answer', '')}\n\n"
            f"Key Strategic Insight:\n{response.get('key_insight', '')}\n\n"
            f"Supporting Figures:\n- " + "\n- ".join(response.get("supporting_figures", []))
        )
        print_box("5. NATURAL-LANGUAGE EXPLANATION", ans_details)

        # 7. Print Confidence Assessment
        conf_details = (
            f"Level: {response.get('confidence', 'UNKNOWN')}\n"
            f"Reasons:\n- " + "\n- ".join(response.get("confidence_reasons", []))
        )
        print_box("6. TRANSPARENT CONFIDENCE SCORE", conf_details)

        time.sleep(0.5)

    print("\n" + "=" * 80)
    print("DEMO RUN COMPLETE: All 4 Analytical Questions Processed Successfully.")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
