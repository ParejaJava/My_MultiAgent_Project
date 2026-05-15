"""Minimal retrieval agent."""

from app.rag.retriever import retrieve_documents
from app.schemas.diagnosis import FaultContext


def retrieve_evidence(context: FaultContext) -> list[str]:
    """Retrieve evidence for the current fault context."""
    query = " ".join(part for part in [context.service, context.description] if part)
    documents = retrieve_documents(query)
    return [
        f"{document.metadata.get('source', 'unknown')}: {document.content}"
        for document in documents
    ]
