"""Embedding providers compatible with Chroma."""

from hashlib import sha256
from importlib import import_module
import math
import os
from pathlib import Path
from typing import Any, cast

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import settings
from app.rag.config import get_embedding_config
from app.rag.model_cache import configure_model_cache


def _as_embeddings(vectors: list[list[float]]) -> Embeddings:
    """Return Python float vectors in the shape Chroma accepts at runtime."""
    return cast(Embeddings, vectors)


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    """Create small deterministic embeddings without external model calls."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    @staticmethod
    def name() -> str:
        """Return a stable Chroma embedding function name."""
        return "hash_embedding"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HashEmbeddingFunction":
        """Build this embedding function from Chroma config."""
        return HashEmbeddingFunction(dimensions=int(config.get("dimensions", 64)))

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {"dimensions": self.dimensions}

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents using hashed token buckets."""
        return _as_embeddings([self._embed(document) for document in input])

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbeddingFunction(EmbeddingFunction[Documents]):
    """OpenAI embedding provider for Chroma."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai embedding provider")
        try:
            openai_module = import_module("openai")
        except ModuleNotFoundError as exc:
            raise ImportError("The openai package is required for the openai embedding provider") from exc

        self.model = model
        self.client: Any = cast(Any, openai_module).OpenAI(api_key=api_key)

    @staticmethod
    def name() -> str:
        """Return a stable Chroma embedding function name."""
        return "openai_embedding"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "OpenAIEmbeddingFunction":
        """Build this embedding function from Chroma config."""
        return OpenAIEmbeddingFunction(model=str(config.get("model", "text-embedding-3-small")))

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {"model": self.model}

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents with the OpenAI embeddings API."""
        response = self.client.embeddings.create(model=self.model, input=list(input))
        return _as_embeddings([list(item.embedding) for item in response.data])


class BGEFlagEmbeddingFunction(EmbeddingFunction[Documents]):
    """Local BGE embedding provider backed by FlagEmbedding.FlagModel."""

    def __init__(
        self,
        model: str = "BAAI/bge-base-zh-v1.5",
        normalize_embeddings: bool = True,
        max_length: int = 512,
        batch_size: int = 16,
        use_fp16: bool = True,
        devices: list[str] | str | None = None,
        cache_folder: str | None = None,
    ) -> None:
        if cache_folder or not is_local_model_path(model):
            configure_model_cache(cache_folder or settings.model_cache_path)
        try:
            flag_embedding_module = import_module("FlagEmbedding")
        except ModuleNotFoundError as exc:
            raise ImportError(
                "FlagEmbedding is required for the bge_local embedding provider"
            ) from exc

        self.model_name = model
        self.normalize_embeddings = normalize_embeddings
        self.max_length = max_length
        self.batch_size = batch_size
        self.use_fp16 = use_fp16
        self.devices = normalize_devices(devices) if devices is not None else None
        kwargs: dict[str, Any] = {
            "normalize_embeddings": normalize_embeddings,
            "use_fp16": use_fp16,
        }
        if self.devices is not None:
            kwargs["devices"] = self.devices
        self.model: Any = cast(Any, flag_embedding_module).FlagModel(model, **kwargs)

    @staticmethod
    def name() -> str:
        """Return a stable Chroma embedding function name."""
        return "bge_flag_embedding"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "BGEFlagEmbeddingFunction":
        """Build this embedding function from Chroma config."""
        return BGEFlagEmbeddingFunction(
            model=str(config.get("model", "BAAI/bge-base-zh-v1.5")),
            normalize_embeddings=bool(config.get("normalize_embeddings", True)),
            max_length=int(config.get("max_length", 512)),
            batch_size=int(config.get("batch_size", 16)),
            use_fp16=bool(config.get("use_fp16", True)),
            devices=config.get("devices"),
            cache_folder=config.get("cache_folder"),
        )

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {
            "model": self.model_name,
            "normalize_embeddings": self.normalize_embeddings,
            "max_length": self.max_length,
            "batch_size": self.batch_size,
            "use_fp16": self.use_fp16,
            "devices": self.devices,
        }

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents with a local BGE model."""
        texts = list(input)
        embeddings = self.model.encode(texts, batch_size=self.batch_size, max_length=self.max_length)
        return _as_embeddings(to_float_vectors(embeddings))


def normalize_devices(devices: list[str] | str) -> list[str]:
    """Normalize devices from YAML scalar/list values for FlagModel."""
    if isinstance(devices, str):
        return [device.strip() for device in devices.split(",") if device.strip()]
    return devices


def is_local_model_path(model: str) -> bool:
    """Return whether a model string points to a local filesystem path."""
    return Path(model).expanduser().is_absolute() or Path(model).exists()


def to_float_vectors(values: Any) -> list[list[float]]:
    """Convert tensor, ndarray, or Python sequence embeddings to list vectors."""
    if hasattr(values, "detach"):
        values = values.detach().cpu()
    if hasattr(values, "numpy"):
        values = values.numpy()
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [[float(value) for value in vector] for vector in values]


def create_embedding_function(config: dict[str, Any]) -> EmbeddingFunction[Documents]:
    """Create a Chroma-compatible embedding function from RAG config."""
    embedding = get_embedding_config(config)
    provider = str(embedding.get("provider", "")).lower()

    if provider == "hash":
        return HashEmbeddingFunction(dimensions=int(embedding.get("dimensions", 64)))
    if provider == "openai":
        return OpenAIEmbeddingFunction(model=str(embedding.get("model", "text-embedding-3-small")))
    if provider == "bge_local":
        return BGEFlagEmbeddingFunction(
            model=str(embedding.get("model", "BAAI/bge-base-zh-v1.5")),
            normalize_embeddings=bool(embedding.get("normalize_embeddings", True)),
            max_length=int(embedding.get("max_length", 512)),
            batch_size=int(embedding.get("batch_size", 16)),
            use_fp16=bool(embedding.get("use_fp16", True)),
            devices=embedding.get("devices"),
            cache_folder=embedding.get("cache_folder"),
        )

    raise ValueError(
        "Unsupported embedding provider. Expected one of: hash, openai, bge_local; "
        f"got {provider or '<missing>'}"
    )
