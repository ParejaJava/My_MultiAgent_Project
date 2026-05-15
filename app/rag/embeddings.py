"""Deterministic local embeddings for the minimal Chroma store."""

from hashlib import sha256
import math

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    """Create small deterministic embeddings without external model calls."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def name(self) -> str:
        """Return a stable Chroma embedding function name."""
        return "hash_embedding"

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
