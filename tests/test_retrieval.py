from pathlib import Path
from typing import Any
from uuid import uuid4

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import project_relative_source
from app.rag.retriever import retrieve_documents
from app.rag.splitter import split_text
from app.rag.vector_store import ingest_documents, query_documents


def test_split_text_uses_overlap() -> None:
    chunks = split_text("abcdef", chunk_size=4, overlap=2)

    assert chunks == ["abcd", "cdef"]


def test_retrieve_documents_returns_source_metadata(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "timeouts.md"
    source.write_text(
        "# Timeout Guide\n\nTimeout errors can come from downstream latency.",
        encoding="utf-8",
    )

    persist_dir = tmp_path / "chroma"
    config_path = write_hash_rag_config(tmp_path)
    count = ingest_documents(
        docs_dir=docs_dir,
        persist_directory=persist_dir,
        chunk_size=80,
        overlap=10,
    )
    results = retrieve_documents("timeout latency", persist_directory=persist_dir, config_path=config_path)

    assert count >= 1
    assert results
    assert results[0].content
    assert results[0].metadata["source"] == project_relative_source(source)
    assert "chunk_index" in results[0].metadata


def test_non_hash_embedding_results_are_not_lexically_filtered(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "semantic.md"
    source.write_text("完全不同的文档内容", encoding="utf-8")

    persist_dir = tmp_path / "chroma"
    embedding = ConstantEmbeddingFunction()
    collection_name = f"test_semantic_{uuid4().hex}"
    ingest_documents(
        docs_dir=docs_dir,
        persist_directory=persist_dir,
        collection_name=collection_name,
        chunk_size=80,
        overlap=10,
        embedding_function=embedding,
    )

    results = query_documents(
        "unrelated query terms",
        persist_directory=persist_dir,
        collection_name=collection_name,
        embedding_function=embedding,
    )

    assert results
    assert results[0].metadata["source"] == project_relative_source(source)


class ConstantEmbeddingFunction(EmbeddingFunction[Documents]):
    def name(self) -> str:
        return "constant_embedding"

    def get_config(self) -> dict[str, Any]:
        return {}

    def __call__(self, input: Documents) -> Embeddings:
        return [[1.0, 0.0, 0.0] for _ in input]


def write_hash_rag_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "hash_rag.yaml"
    config_path.write_text(
        "\n".join(
            [
                "name: test_hash",
                "retriever: dense",
                "collection_name: ops_knowledge_base_hash",
                "embedding:",
                "  provider: hash",
                "  dimensions: 64",
            ]
        ),
        encoding="utf-8",
    )
    return config_path
