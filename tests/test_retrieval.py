from pathlib import Path
from uuid import uuid4

from app.rag.retriever import retrieve_documents
from app.rag.splitter import split_text
from app.rag.vector_store import ingest_documents


def test_split_text_uses_overlap() -> None:
    chunks = split_text("abcdef", chunk_size=4, overlap=2)

    assert chunks == ["abcd", "cdef"]


def test_retrieve_documents_returns_source_metadata() -> None:
    test_dir = Path("tests") / ".tmp_rag" / uuid4().hex
    docs_dir = test_dir / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "timeouts.md"
    source.write_text(
        "# Timeout Guide\n\nTimeout errors can come from downstream latency.",
        encoding="utf-8",
    )

    persist_dir = test_dir / "chroma"
    count = ingest_documents(
        docs_dir=docs_dir,
        persist_directory=persist_dir,
        chunk_size=80,
        overlap=10,
    )
    results = retrieve_documents("timeout latency", persist_directory=persist_dir)

    assert count >= 1
    assert results
    assert results[0].content
    assert results[0].metadata["source"] == source.as_posix()
    assert "chunk_index" in results[0].metadata
