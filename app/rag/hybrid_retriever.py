"""Hybrid dense + BM25 retrieval with RRF fusion."""

from pathlib import Path
from typing import Any

from app.config import settings
from app.rag.bm25_store import search_bm25_documents
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, get_collection_name, load_rag_config
from app.rag.embeddings import create_embedding_function
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.vector_store import RetrievedDocument, query_documents


def retrieve_hybrid_documents(
    query: str,
    top_k: int = 3,
    persist_directory: Path | str = settings.vector_store_path,
    config_path: Path | str | None = None,
) -> list[RetrievedDocument]:
    """Retrieve documents with dense and BM25 retrievers, then fuse with RRF."""
    config = load_rag_config(config_path or DEFAULT_RAG_CONFIG_PATH)
    ranking = config.get("ranking", {}) if isinstance(config.get("ranking"), dict) else {}
    chunking = config.get("chunking", {}) if isinstance(config.get("chunking"), dict) else {}

    top_n = int(ranking.get("top_n", max(top_k * 2, top_k)))
    rrf_k = int(ranking.get("rrf_k", 60))
    docs_dir = config.get("docs_dir", "data/docs")
    chunk_size = int(chunking.get("chunk_size", 500))
    overlap = int(chunking.get("overlap", 50))

    dense_results = query_documents(
        query=query,
        top_k=top_n,
        persist_directory=persist_directory,
        collection_name=get_collection_name(config),
        embedding_function=create_embedding_function(config),
    )
    dense_results = [
        _with_rank_metadata(document, retrieval_method="dense", rank=rank)
        for rank, document in enumerate(dense_results, start=1)
    ]
    bm25_results = search_bm25_documents(
        query=query,
        top_n=top_n,
        docs_dir=docs_dir,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    return reciprocal_rank_fusion([dense_results, bm25_results], rrf_k=rrf_k, top_k=top_k)


def _with_rank_metadata(document: RetrievedDocument, retrieval_method: str, rank: int) -> RetrievedDocument:
    metadata: dict[str, Any] = {
        **document.metadata,
        "retrieval_method": retrieval_method,
    }
    if retrieval_method == "dense":
        metadata["dense_rank"] = rank
    elif retrieval_method == "bm25":
        metadata["bm25_rank"] = rank
    return RetrievedDocument(content=document.content, metadata=metadata, score=document.score)
