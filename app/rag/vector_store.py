"""Chroma vector store helpers."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import chromadb
from chromadb.api import ClientAPI

from app.config import settings
from app.rag.embeddings import HashEmbeddingFunction
from app.rag.loader import load_markdown_documents
from app.rag.splitter import split_text


DEFAULT_COLLECTION_NAME = "ops_knowledge_base"
_MEMORY_CLIENTS: dict[str, ClientAPI] = {}


@dataclass(frozen=True)
class RetrievedDocument:
    """A retrieved document chunk with source metadata."""

    content: str
    metadata: dict[str, Any]
    score: float | None = None


def ingest_documents(
    docs_dir: Path | str = Path("data/docs"),
    persist_directory: Path | str = settings.vector_store_path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    chunk_size: int = 500,
    overlap: int = 50,
    reset_collection: bool = True,
) -> int:
    """Load markdown documents, split them, and store chunks in Chroma."""
    docs_path = Path(docs_dir)
    client = _get_chroma_client(persist_directory)
    if reset_collection:
        _delete_collection_if_exists(client, collection_name)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=HashEmbeddingFunction(),
    )

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for path, text in load_markdown_documents(docs_path):
        source = path.as_posix()
        for chunk_index, chunk in enumerate(split_text(text, chunk_size, overlap)):
            ids.append(f"{source}:{chunk_index}")
            documents.append(chunk)
            metadatas.append({"source": source, "chunk_index": chunk_index})

    if not documents:
        return 0

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(documents)


def query_documents(
    query: str,
    top_k: int = 3,
    persist_directory: Path | str = settings.vector_store_path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> list[RetrievedDocument]:
    """Return the top matching Chroma document chunks for a query."""
    if not query.strip() or top_k <= 0:
        return []

    try:
        client = _get_chroma_client(persist_directory)
        collection = client.get_collection(
            name=collection_name,
            embedding_function=HashEmbeddingFunction(),
        )
        if collection.count() == 0:
            return []
        results = collection.query(query_texts=[query], n_results=top_k)
    except Exception:
        return []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved: list[RetrievedDocument] = []
    query_terms = _tokenize(query)
    for index, content in enumerate(documents):
        if query_terms and not query_terms.intersection(_tokenize(content)):
            continue
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        distance = distances[index] if index < len(distances) else None
        score = None if distance is None else 1.0 / (1.0 + float(distance))
        retrieved.append(RetrievedDocument(content=content, metadata=dict(metadata), score=score))
    return retrieved


def _get_chroma_client(persist_directory: Path | str) -> ClientAPI:
    """Return a persistent Chroma client, falling back to memory if persistence fails."""
    path = str(persist_directory)
    try:
        return chromadb.PersistentClient(path=path)
    except Exception:
        if path not in _MEMORY_CLIENTS:
            _MEMORY_CLIENTS[path] = chromadb.Client()
        return _MEMORY_CLIENTS[path]


def _delete_collection_if_exists(client: ClientAPI, collection_name: str) -> None:
    try:
        client.delete_collection(collection_name)
    except Exception:
        return


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(token) > 2
    }
