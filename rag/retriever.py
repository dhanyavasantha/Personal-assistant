from rag.vector_store import get_vectorstore


def get_relevant_context(query: str, k: int = 4) -> str:
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(query, k=k)

    return "\n\n".join(
        f"[Source: {d.metadata.get('source')}]\n{d.page_content}"
        for d in docs
    )
