"""Document retrieval interface."""

from pathlib import Path

from app.config import settings
from app.rag.vector_store import RetrievedDocument, query_documents


def retrieve_documents(
    query: str,
    top_k: int = 3,
    persist_directory: Path | str = settings.vector_store_path,
) -> list[RetrievedDocument]:
    """Retrieve top document chunks with source metadata."""
    return query_documents(query=query, top_k=top_k, persist_directory=persist_directory)
