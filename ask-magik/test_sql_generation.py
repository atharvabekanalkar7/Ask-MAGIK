"""
Test Structured SQL Generation with Ollama
"""

from backend.rag.retriever import KnowledgeRetriever
from backend.llm.ollama_client import OllamaClient

def main():
    retriever = KnowledgeRetriever()
    client = OllamaClient()

    question = "How many customers churned by region?"
    pkg = retriever.retrieve(question)
    context_text = pkg.get_full_prompt_context()

    print("Sending question to Ollama...")
    try:
        result = client.generate_structured_sql(question, context_text)
        print("Question Understanding:", result.question_understanding)
        print("Tables Needed:", result.tables_needed)
        print("Generated SQL:", result.sql)
        print("Assumptions:", result.assumptions)
    except ConnectionError as e:
        print(f"Ollama offline: {e}")


if __name__ == "__main__":
    main()
