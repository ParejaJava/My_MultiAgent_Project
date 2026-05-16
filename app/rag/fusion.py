"""Rank fusion helpers."""

from app.rag.vector_store import RetrievedDocument


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedDocument]],
    rrf_k: int = 60,
    top_k: int = 3,
) -> list[RetrievedDocument]:
    """Fuse ranked retrieval lists using reciprocal rank fusion."""
    fused: dict[tuple[str, int], dict[str, object]] = {}

    for ranked_list in ranked_lists:
        for rank, document in enumerate(ranked_list, start=1):
            source = str(document.metadata.get("source", ""))
            chunk_index = int(document.metadata.get("chunk_index", -1))
            key = (source, chunk_index)
            item = fused.setdefault(
                key,
                {
                    "document": document,
                    "rrf_score": 0.0,
                    "dense_rank": None,
                    "bm25_rank": None,
                    "methods": set(),
                },
            )
            item["rrf_score"] = float(item["rrf_score"]) + 1.0 / (rrf_k + rank)
            methods = item["methods"]
            if isinstance(methods, set):
                method = document.metadata.get("retrieval_method")
                if method:
                    methods.add(str(method))
            if document.metadata.get("dense_rank") is not None:
                item["dense_rank"] = document.metadata["dense_rank"]
            if document.metadata.get("bm25_rank") is not None:
                item["bm25_rank"] = document.metadata["bm25_rank"]

    sorted_items = sorted(
        fused.values(),
        key=lambda item: float(item["rrf_score"]),
        reverse=True,
    )

    results: list[RetrievedDocument] = []
    for item in sorted_items[:top_k]:
        document = item["document"]
        if not isinstance(document, RetrievedDocument):
            continue
        methods = item["methods"]
        method_names = sorted(methods) if isinstance(methods, set) else []
        metadata = {
            **document.metadata,
            "retrieval_method": "+".join(method_names) if method_names else "hybrid_rrf",
            "dense_rank": item["dense_rank"],
            "bm25_rank": item["bm25_rank"],
            "rrf_score": float(item["rrf_score"]),
        }
        results.append(RetrievedDocument(content=document.content, metadata=metadata, score=float(item["rrf_score"])))
    return results
