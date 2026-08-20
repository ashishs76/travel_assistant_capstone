from ..rag import retriever


def retrieve_node(state: dict) -> dict:
    context = retriever.retrieve_destination_context(state["destination"])
    return {"rag_context": context}