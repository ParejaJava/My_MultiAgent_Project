"""Reranker providers for retrieval results."""

from pathlib import Path
from typing import Any, Protocol

from app.config import settings
from app.rag.model_cache import configure_model_cache
from app.rag.vector_store import RetrievedDocument


class Reranker(Protocol):
    """Protocol for retrieval rerankers."""

    def rerank(self, query: str, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """Return reranked documents."""


class NoneReranker:
    """No-op reranker that preserves the original order."""

    def rerank(self, query: str, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """Preserve document order while adding rank metadata."""
        return [
            RetrievedDocument(
                content=document.content,
                metadata={
                    **document.metadata,
                    "original_rank": rank,
                    "final_rank": rank,
                    "rerank_score": None,
                },
                score=document.score,
            )
            for rank, document in enumerate(documents, start=1)
        ]


class BGEFlagReranker:
    """BGE reranker backed by FlagEmbedding.FlagReranker."""

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-base",
        cache_folder: str | None = None,
        use_fp16: bool = True,
        devices: list[str] | str | None = None,
        query_max_length: int = 256,
        passage_max_length: int = 512,
        batch_size: int = 16,
    ) -> None:
        if cache_folder or not is_local_model_path(model):
            configure_model_cache(cache_folder or settings.model_cache_path)
        try:
            from FlagEmbedding import FlagReranker
        except ModuleNotFoundError as exc:
            raise ImportError(
                "FlagEmbedding is required for reranker provider 'bge'. "
                "Install it before using BGE reranking."
            ) from exc

        self.model_name = model
        self.query_max_length = query_max_length
        self.passage_max_length = passage_max_length
        self.batch_size = batch_size
        kwargs: dict[str, Any] = {
            "query_max_length": query_max_length,
            "use_fp16": use_fp16,
        }
        if devices is not None:
            kwargs["devices"] = normalize_devices(devices)
        self.reranker = FlagReranker(model, **kwargs)

    def rerank(self, query: str, documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """Score query-document pairs and sort by rerank_score descending."""
        if not documents:
            return []

        pairs = [
            [
                truncate_text(query, self.query_max_length),
                truncate_text(document.content, self.passage_max_length),
            ]
            for document in documents
        ]
        scores = self._compute_scores(pairs)
        ranked = sorted(
            zip(documents, scores, range(1, len(documents) + 1), strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        return [
            RetrievedDocument(
                content=document.content,
                metadata={
                    **document.metadata,
                    "original_rank": original_rank,
                    "final_rank": final_rank,
                    "rerank_score": float(score),
                },
                score=float(score),
            )
            for final_rank, (document, score, original_rank) in enumerate(ranked, start=1)
        ]

    def _compute_scores(self, pairs: list[list[str]]) -> list[float]:
        try:
            scores = self.reranker.compute_score(pairs, batch_size=self.batch_size)
        except TypeError:
            scores = self.reranker.compute_score(pairs)
        return to_float_list(scores)


def to_float_list(values: Any) -> list[float]:
    """Convert tensor, ndarray, scalar, or nested sequence scores to floats."""
    if hasattr(values, "detach"):
        values = values.detach().cpu()
    if hasattr(values, "numpy"):
        values = values.numpy()
    if hasattr(values, "tolist"):
        values = values.tolist()
    if isinstance(values, int | float):
        return [float(values)]
    if values and isinstance(values[0], list):
        values = values[0]
    return [float(value) for value in values]


def normalize_devices(devices: list[str] | str) -> list[str]:
    """Normalize devices from YAML scalar/list values for FlagReranker."""
    if isinstance(devices, str):
        return [device.strip() for device in devices.split(",") if device.strip()]
    return devices


def is_local_model_path(model: str) -> bool:
    """Return whether a model string points to a local filesystem path."""
    return Path(model).expanduser().is_absolute() or Path(model).exists()


def create_reranker(config: dict[str, Any]) -> Reranker:
    """Create a reranker from RAG config."""
    reranker_config = config.get("reranker", {})
    if reranker_config is None:
        reranker_config = {}
    if not isinstance(reranker_config, dict):
        raise ValueError("RAG config field 'reranker' must be a mapping")

    provider = str(reranker_config.get("provider", "none")).lower()
    if provider == "none":
        return NoneReranker()
    if provider == "bge":
        return BGEFlagReranker(
            model=str(reranker_config.get("model", "BAAI/bge-reranker-base")),
            cache_folder=reranker_config.get("cache_folder"),
            use_fp16=bool(reranker_config.get("use_fp16", True)),
            devices=reranker_config.get("devices"),
            query_max_length=int(reranker_config.get("query_max_length", 256)),
            passage_max_length=int(reranker_config.get("passage_max_length", 512)),
            batch_size=int(reranker_config.get("batch_size", 16)),
        )

    raise ValueError(
        "Unsupported reranker provider. Expected one of: none, bge; "
        f"got {provider or '<missing>'}"
    )


def rerank_documents(
    query: str,
    documents: list[RetrievedDocument],
    config: dict[str, Any],
) -> list[RetrievedDocument]:
    """Rerank documents using the provider configured in RAG config."""
    return create_reranker(config).rerank(query, documents)


def get_reranker_metadata(config: dict[str, Any], retrieve_top_n: int, rerank_top_k: int) -> dict[str, Any]:
    """Return reranker metadata for evaluation reports."""
    reranker_config = config.get("reranker", {})
    if reranker_config is None:
        reranker_config = {}
    if not isinstance(reranker_config, dict):
        reranker_config = {}
    provider = str(reranker_config.get("provider", "none")).lower()
    return {
        "enabled": provider != "none",
        "provider": provider,
        "model": reranker_config.get("model"),
        "retrieve_top_n": retrieve_top_n,
        "rerank_top_k": rerank_top_k,
    }


def truncate_text(text: str, max_length: int) -> str:
    """Conservatively truncate text before passing it to a reranker."""
    if max_length <= 0:
        return text
    return text[:max_length]
