"""Local BM25 retrieval over markdown document chunks."""

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Any

from app.rag.loader import load_markdown_documents
from app.rag.splitter import split_text
from app.rag.vector_store import RetrievedDocument


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class BM25Chunk:
    """A document chunk indexed by BM25."""

    content: str
    metadata: dict[str, Any]
    tokens: list[str]


class BM25Store:
    """Small in-memory BM25 store for local markdown chunks."""

    def __init__(self, chunks: list[BM25Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.avg_doc_len = (
            sum(len(chunk.tokens) for chunk in chunks) / len(chunks)
            if chunks
            else 0.0
        )
        self.doc_freq = self._build_doc_freq(chunks)

    @classmethod
    def from_docs_dir(
        cls,
        docs_dir: Path | str = Path("data/docs"),
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> "BM25Store":
        """Build a BM25 store from markdown documents."""
        chunks: list[BM25Chunk] = []
        for path, text in load_markdown_documents(Path(docs_dir)):
            source = path.as_posix()
            for chunk_index, chunk in enumerate(split_text(text, chunk_size, overlap)):
                chunks.append(
                    BM25Chunk(
                        content=chunk,
                        metadata={"source": source, "chunk_index": chunk_index},
                        tokens=tokenize(chunk),
                    )
                )
        return cls(chunks)

    def search(self, query: str, top_n: int = 10) -> list[RetrievedDocument]:
        """Search chunks with BM25 and return top results."""
        query_tokens = tokenize(query)
        if not query_tokens or top_n <= 0 or not self.chunks:
            return []

        scored: list[tuple[float, BM25Chunk]] = []
        for chunk in self.chunks:
            score = self._score(query_tokens, chunk)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedDocument(
                content=chunk.content,
                metadata={
                    **chunk.metadata,
                    "retrieval_method": "bm25",
                    "bm25_rank": rank,
                },
                score=score,
            )
            for rank, (score, chunk) in enumerate(scored[:top_n], start=1)
        ]

    def _score(self, query_tokens: list[str], chunk: BM25Chunk) -> float:
        token_counts: dict[str, int] = {}
        for token in chunk.tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        score = 0.0
        doc_len = len(chunk.tokens)
        for token in query_tokens:
            term_freq = token_counts.get(token, 0)
            if term_freq == 0:
                continue
            score += self._idf(token) * (
                (term_freq * (self.k1 + 1))
                / (
                    term_freq
                    + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_len, 1.0))
                )
            )
        return score

    def _idf(self, token: str) -> float:
        doc_count = len(self.chunks)
        freq = self.doc_freq.get(token, 0)
        return math.log(1 + (doc_count - freq + 0.5) / (freq + 0.5))

    @staticmethod
    def _build_doc_freq(chunks: list[BM25Chunk]) -> dict[str, int]:
        doc_freq: dict[str, int] = {}
        for chunk in chunks:
            for token in set(chunk.tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1
        return doc_freq


def tokenize(text: str) -> list[str]:
    """Tokenize English identifiers, numbers, and Chinese text blocks."""
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def search_bm25_documents(
    query: str,
    top_n: int = 10,
    docs_dir: Path | str = Path("data/docs"),
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[RetrievedDocument]:
    """Build a local BM25 store and search it."""
    return BM25Store.from_docs_dir(docs_dir, chunk_size, overlap).search(query, top_n)
