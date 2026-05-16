"""Embedding providers compatible with Chroma."""

from hashlib import sha256
import math
import os
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.rag.config import get_embedding_config


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    """Create small deterministic embeddings without external model calls."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def name(self) -> str:
        """Return a stable Chroma embedding function name."""
        return "hash_embedding"

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {"dimensions": self.dimensions}

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents using hashed token buckets."""
        return [self._embed(document) for document in input]

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
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ImportError("The openai package is required for the openai embedding provider") from exc

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def name(self) -> str:
        """Return a stable Chroma embedding function name."""
        return "openai_embedding"

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {"model": self.model}

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents with the OpenAI embeddings API."""
        response = self.client.embeddings.create(model=self.model, input=list(input))
        return [item.embedding for item in response.data]


class BGELocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """Local BGE embedding provider backed by sentence-transformers."""

    def __init__(self, model: str = "BAAI/bge-small-zh-v1.5", normalize_embeddings: bool = True) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise ImportError(
                "sentence-transformers is required for the bge_local embedding provider"
            ) from exc

        self.model_name = model
        self.normalize_embeddings = normalize_embeddings
        self.model = SentenceTransformer(model)

    def name(self) -> str:
        """Return a stable Chroma embedding function name."""
        return "bge_local_embedding"

    def get_config(self) -> dict[str, Any]:
        """Return Chroma embedding function config."""
        return {
            "model": self.model_name,
            "normalize_embeddings": self.normalize_embeddings,
        }

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents with a local BGE model."""
        embeddings = self.model.encode(
            list(input),
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embeddings.tolist()


def create_embedding_function(config: dict[str, Any]) -> EmbeddingFunction[Documents]:
    """Create a Chroma-compatible embedding function from RAG config."""
    embedding = get_embedding_config(config)
    provider = str(embedding.get("provider", "")).lower()

    if provider == "hash":
        return HashEmbeddingFunction(dimensions=int(embedding.get("dimensions", 64)))
    if provider == "openai":
        return OpenAIEmbeddingFunction(model=str(embedding.get("model", "text-embedding-3-small")))
    if provider == "bge_local":
        return BGELocalEmbeddingFunction(
            model=str(embedding.get("model", "BAAI/bge-small-zh-v1.5")),
            normalize_embeddings=bool(embedding.get("normalize_embeddings", True)),
        )

    raise ValueError(
        "Unsupported embedding provider. Expected one of: hash, openai, bge_local; "
        f"got {provider or '<missing>'}"
    )
