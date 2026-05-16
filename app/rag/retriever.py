"""Document retrieval interface."""

from pathlib import Path

from app.config import settings
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, get_collection_name, load_rag_config
from app.rag.embeddings import create_embedding_function
from app.rag.vector_store import RetrievedDocument, query_documents


def retrieve_documents(
    query: str,
    top_k: int = 3,
    persist_directory: Path | str = settings.vector_store_path,
    config_path: Path | str | None = None,
) -> list[RetrievedDocument]:
    """Retrieve top document chunks with source metadata."""
    config = load_rag_config(config_path or DEFAULT_RAG_CONFIG_PATH)
    return query_documents(
        query=query,
        top_k=top_k,
        persist_directory=persist_directory,
        collection_name=get_collection_name(config),
        embedding_function=create_embedding_function(config),
    )
