"""Hybrid dense + BM25 retrieval with RRF fusion."""

from pathlib import Path
from typing import Any

from app.config import settings
from app.rag.bm25_store import search_bm25_documents
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, get_collection_name, load_rag_config
from app.rag.embeddings import create_embedding_function
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.reranker import rerank_documents
from app.rag.vector_store import RetrievedDocument, query_documents


def retrieve_hybrid_documents(
    query: str,
    top_k: int = 3,
    persist_directory: Path | str | None = None,
    config_path: Path | str | None = None,
) -> list[RetrievedDocument]:
    """Retrieve documents with dense and BM25 retrievers, then fuse with RRF."""
    config = load_rag_config(config_path or DEFAULT_RAG_CONFIG_PATH)
    ranking = config.get("ranking", {}) if isinstance(config.get("ranking"), dict) else {}
    chunking = config.get("chunking", {}) if isinstance(config.get("chunking"), dict) else {}
    bm25_config = config.get("bm25", {}) if isinstance(config.get("bm25"), dict) else {}

    retrieve_top_n = int(ranking.get("retrieve_top_n", ranking.get("top_n", max(top_k * 2, top_k))))
    rerank_top_k = int(ranking.get("rerank_top_k", top_k))
    rrf_k = int(ranking.get("rrf_k", 60))
    docs_dir = config.get("docs_dir", "data/docs")
    raw_docs_dirs = config.get("docs_dirs")
    docs_dirs = [str(path) for path in raw_docs_dirs] if isinstance(raw_docs_dirs, list) else None
    chunk_size = int(chunking.get("chunk_size", 500))
    overlap = int(chunking.get("overlap", 50))
    chunking_strategy = str(chunking.get("strategy", "character"))
    bm25_index_directory = bm25_config.get("index_directory", settings.bm25_index_path)
    bm25_k1 = float(bm25_config.get("k1", 1.5))
    bm25_b = float(bm25_config.get("b", 0.75))
    bm25_user_dict = bm25_config.get("user_dict", settings.jieba_user_dict_path)
    configured_persist_directory = persist_directory or config.get("persist_directory") or settings.vector_store_path

    dense_results = query_documents(
        query=query,
        top_k=retrieve_top_n,
        persist_directory=configured_persist_directory,
        collection_name=get_collection_name(config),
        embedding_function=create_embedding_function(config),
    )
    dense_results = [
        _with_rank_metadata(document, retrieval_method="dense", rank=rank)
        for rank, document in enumerate(dense_results, start=1)
    ]
    bm25_results = search_bm25_documents(
        query=query,
        top_n=retrieve_top_n,
        docs_dir=docs_dir,
        docs_dirs=docs_dirs,
        chunk_size=chunk_size,
        overlap=overlap,
        chunking_strategy=chunking_strategy,
        index_directory=bm25_index_directory,
        k1=bm25_k1,
        b=bm25_b,
        user_dict=bm25_user_dict,
    )
    fused_results = reciprocal_rank_fusion(
        [dense_results, bm25_results],
        rrf_k=rrf_k,
        top_k=retrieve_top_n,
    )
    reranked_results = rerank_documents(query, fused_results, config)
    return reranked_results[:rerank_top_k]


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
