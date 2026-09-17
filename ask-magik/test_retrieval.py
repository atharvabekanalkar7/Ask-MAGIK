"""
Test RAG Retrieval for the 4 Demo Questions
"""

from backend.rag.retriever import KnowledgeRetriever

retriever = KnowledgeRetriever()
questions = [
    "Which prepaid plans had the highest customer loss in the western region last month?",
    "How did the Ramadan data-bundle campaign perform compared to the same campaign last year, by region?",
    "Show me postpaid small-business customers whose usage dropped more than 30% in the last 60 days.",
    "What is driving the rise in early customer loss this quarter - channel or customer type?",
]

for idx, q in enumerate(questions, 1):
    pkg = retriever.retrieve(q)
    print(f"=== Q{idx}: {q} ===")
    print(f"Top tables identified: {pkg.top_tables}")
    print(f"Retrieved {len(pkg.chunks)} chunks:")
    for c in pkg.chunks[:4]:
        st = c["source_type"].upper()
        did = c["doc_id"]
        score = c["final_score"]
        print(f"  - [{st}] {did} (score: {score})")
    print()
