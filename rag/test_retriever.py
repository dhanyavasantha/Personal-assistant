from rag.retriever import get_relevant_context

query = "Should I schedule meetings immediately after travel?"

context = get_relevant_context(query)

print(context)
