"""Local BM25 retrieval over markdown document chunks."""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from app.config import project_relative_source, resolve_project_path, settings
from app.rag.loader import load_markdown_documents
from app.rag.splitter import split_text
from app.rag.storage_check import ensure_directory_ready
from app.rag.vector_store import RetrievedDocument


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")
BM25_INDEX_VERSION = "bm25-chunk-jieba-v1"
DEFAULT_INDEX_DIR = Path(settings.bm25_index_path)
DEFAULT_USER_DICT = Path(settings.jieba_user_dict_path)
_LOADED_USER_DICTS: set[str] = set()


@dataclass(frozen=True)
class MarkdownDocument:
    """A markdown document loaded for BM25 indexing."""

    source: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class BM25Chunk:
    """A document chunk indexed by BM25."""

    content: str
    metadata: dict[str, Any]
    tokens: list[str]


class BM25Store:
    """Small in-memory BM25 store for local markdown chunks."""

    def __init__(
        self,
        chunks: list[BM25Chunk],
        k1: float = 1.5,
        b: float = 0.75,
        user_dict: Path | str | None = DEFAULT_USER_DICT,
    ) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.user_dict = user_dict
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
        k1: float = 1.5,
        b: float = 0.75,
        user_dict: Path | str | None = DEFAULT_USER_DICT,
    ) -> "BM25Store":
        """Build a BM25 store from markdown documents."""
        return cls.from_documents(load_markdown_document_records(docs_dir), chunk_size, overlap, k1, b, user_dict)

    @classmethod
    def from_documents(
        cls,
        documents: list[MarkdownDocument],
        chunk_size: int = 500,
        overlap: int = 50,
        k1: float = 1.5,
        b: float = 0.75,
        user_dict: Path | str | None = DEFAULT_USER_DICT,
    ) -> "BM25Store":
        """Build a BM25 store from loaded markdown documents."""
        chunks: list[BM25Chunk] = []
        for document in documents:
            for chunk_index, chunk in enumerate(split_text(document.text, chunk_size, overlap)):
                chunks.append(
                    BM25Chunk(
                        content=chunk,
                        metadata={"source": document.source, "chunk_index": chunk_index},
                        tokens=tokenize(chunk, user_dict=user_dict),
                    )
                )
        return cls(chunks, k1=k1, b=b, user_dict=user_dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BM25Store":
        """Restore a BM25 store from persisted JSON data."""
        chunks = [
            BM25Chunk(
                content=str(item["content"]),
                metadata=dict(item["metadata"]),
                tokens=[str(token) for token in item["tokens"]],
            )
            for item in data.get("chunks", [])
            if isinstance(item, dict)
        ]
        return cls(
            chunks=chunks,
            k1=float(data.get("k1", 1.5)),
            b=float(data.get("b", 0.75)),
            user_dict=data.get("strategy", {}).get("user_dict") if isinstance(data.get("strategy"), dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this BM25 store to JSON-compatible data."""
        return {
            "version": BM25_INDEX_VERSION,
            "k1": self.k1,
            "b": self.b,
            "chunks": [
                {
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "tokens": chunk.tokens,
                }
                for chunk in self.chunks
            ],
        }

    def search(self, query: str, top_n: int = 10) -> list[RetrievedDocument]:
        """Search chunks with BM25 and return top results."""
        query_tokens = tokenize(query, user_dict=self.user_dict)
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


def tokenize(text: str, user_dict: Path | str | None = DEFAULT_USER_DICT) -> list[str]:
    """Tokenize English identifiers, numbers, and Chinese text with jieba."""
    jieba = load_jieba(user_dict)

    tokens: list[str] = []
    for match in TOKEN_PATTERN.findall(text):
        if re.fullmatch(r"[a-zA-Z0-9_]+", match):
            tokens.append(match.lower())
        else:
            tokens.extend(token.strip().lower() for token in jieba.lcut(match) if token.strip())
    return tokens


def load_jieba(user_dict: Path | str | None = DEFAULT_USER_DICT) -> Any:
    """Load jieba and an optional project user dictionary once per process."""
    try:
        import jieba
    except ModuleNotFoundError as exc:
        raise ImportError("jieba is required for BM25 Chinese tokenization") from exc

    if user_dict is None:
        return jieba

    user_dict_path = resolve_project_path(user_dict)
    if not user_dict_path.exists():
        return jieba

    user_dict_key = str(user_dict_path)
    load_userdict = getattr(jieba, "load_userdict", None)
    if user_dict_key not in _LOADED_USER_DICTS and callable(load_userdict):
        load_userdict(str(user_dict_path))
        _LOADED_USER_DICTS.add(user_dict_key)
    return jieba


def load_markdown_document_records(docs_dir: Path | str) -> list[MarkdownDocument]:
    """Load markdown documents with stable source names and content hashes."""
    documents: list[MarkdownDocument] = []
    for path, text in load_markdown_documents(resolve_project_path(docs_dir)):
        documents.append(
            MarkdownDocument(
                source=project_relative_source(path),
                text=text,
                content_hash=sha256(text.encode("utf-8")).hexdigest(),
            )
        )
    return documents


def get_or_build_bm25_store(
    docs_dir: Path | str = Path("data/docs"),
    chunk_size: int = 500,
    overlap: int = 50,
    index_directory: Path | str = DEFAULT_INDEX_DIR,
    k1: float = 1.5,
    b: float = 0.75,
    user_dict: Path | str | None = DEFAULT_USER_DICT,
) -> BM25Store:
    """Load a persisted chunk-level BM25 index or build and save it."""
    documents = load_markdown_document_records(docs_dir)
    fingerprint = build_index_fingerprint(
        documents=documents,
        docs_dir=docs_dir,
        chunk_size=chunk_size,
        overlap=overlap,
        k1=k1,
        b=b,
        user_dict=user_dict,
    )
    index_dir = resolve_project_path(index_directory)
    index_path = index_dir / f"{fingerprint}.json"
    if index_path.exists():
        return BM25Store.from_dict(json.loads(index_path.read_text(encoding="utf-8")))

    ensure_directory_ready(index_dir, label="BM25 index directory")
    store = BM25Store.from_documents(
        documents=documents,
        chunk_size=chunk_size,
        overlap=overlap,
        k1=k1,
        b=b,
        user_dict=user_dict,
    )
    payload = {
        "fingerprint": fingerprint,
        "strategy": build_strategy_metadata(docs_dir, chunk_size, overlap, k1, b, user_dict),
        **store.to_dict(),
    }
    write_json_atomic(index_path, payload)
    return store


def build_index_fingerprint(
    documents: list[MarkdownDocument],
    docs_dir: Path | str,
    chunk_size: int,
    overlap: int,
    k1: float,
    b: float,
    user_dict: Path | str | None,
) -> str:
    """Build a fingerprint that changes when docs or BM25 strategy changes."""
    payload = build_strategy_metadata(docs_dir, chunk_size, overlap, k1, b, user_dict)
    payload["documents"] = [
        {
            "source": document.source,
            "content_hash": document.content_hash,
        }
        for document in documents
    ]
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def build_strategy_metadata(
    docs_dir: Path | str,
    chunk_size: int,
    overlap: int,
    k1: float,
    b: float,
    user_dict: Path | str | None = DEFAULT_USER_DICT,
) -> dict[str, Any]:
    """Return metadata defining the BM25 indexing strategy."""
    user_dict_path = resolve_project_path(user_dict) if user_dict is not None else None
    return {
        "version": BM25_INDEX_VERSION,
        "tokenizer": "jieba",
        "user_dict": project_relative_source(user_dict_path) if user_dict_path else None,
        "user_dict_hash": hash_file(user_dict_path) if user_dict_path and user_dict_path.exists() else None,
        "index_granularity": "chunk",
        "docs_dir": project_relative_source(resolve_project_path(docs_dir)),
        "chunk_size": chunk_size,
        "overlap": overlap,
        "k1": k1,
        "b": b,
    }


def search_bm25_documents(
    query: str,
    top_n: int = 10,
    docs_dir: Path | str = Path("data/docs"),
    chunk_size: int = 500,
    overlap: int = 50,
    index_directory: Path | str = DEFAULT_INDEX_DIR,
    k1: float = 1.5,
    b: float = 0.75,
    user_dict: Path | str | None = DEFAULT_USER_DICT,
) -> list[RetrievedDocument]:
    """Search a persisted chunk-level BM25 index."""
    return get_or_build_bm25_store(
        docs_dir=docs_dir,
        chunk_size=chunk_size,
        overlap=overlap,
        index_directory=index_directory,
        k1=k1,
        b=b,
        user_dict=user_dict,
    ).search(query, top_n)


def hash_file(path: Path) -> str:
    """Return the SHA256 hash for a file."""
    return sha256(path.read_bytes()).hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON through a temporary file and atomic replace."""
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary_path, path)
