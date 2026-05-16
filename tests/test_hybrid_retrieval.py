from pathlib import Path
from uuid import uuid4

from app.rag.bm25_store import search_bm25_documents
from app.rag.fusion import reciprocal_rank_fusion
import app.rag.hybrid_retriever as hybrid_retriever
from app.rag.vector_store import RetrievedDocument


def test_reciprocal_rank_fusion_prefers_shared_high_rank_result() -> None:
    shared_dense = RetrievedDocument(
        content="redis timeout",
        metadata={"source": "redis.md", "chunk_index": 0, "retrieval_method": "dense", "dense_rank": 1},
    )
    dense_only = RetrievedDocument(
        content="mysql timeout",
        metadata={"source": "mysql.md", "chunk_index": 0, "retrieval_method": "dense", "dense_rank": 2},
    )
    shared_bm25 = RetrievedDocument(
        content="redis timeout",
        metadata={"source": "redis.md", "chunk_index": 0, "retrieval_method": "bm25", "bm25_rank": 1},
    )

    results = reciprocal_rank_fusion([[shared_dense, dense_only], [shared_bm25]], rrf_k=60, top_k=2)

    assert results[0].metadata["source"] == "redis.md"
    assert results[0].metadata["dense_rank"] == 1
    assert results[0].metadata["bm25_rank"] == 1
    assert results[0].metadata["rrf_score"] > results[1].metadata["rrf_score"]


def test_bm25_retrieves_keyword() -> None:
    test_dir = Path("tests") / ".tmp_hybrid" / uuid4().hex
    docs_dir = test_dir / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "mysql.md"
    source.write_text("MySQL 报错 1205 Lock wait timeout exceeded，需要检查长事务。", encoding="utf-8")

    results = search_bm25_documents("1205", top_n=3, docs_dir=docs_dir, chunk_size=200, overlap=20)

    assert results
    assert results[0].metadata["source"] == source.as_posix()
    assert results[0].metadata["retrieval_method"] == "bm25"
    assert results[0].metadata["bm25_rank"] == 1


def test_hybrid_retriever_returns_required_metadata(monkeypatch) -> None:
    test_dir = Path("tests") / ".tmp_hybrid" / uuid4().hex
    docs_dir = test_dir / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "redis.md"
    source.write_text("Redis READONLY You can't write against a read only replica。", encoding="utf-8")
    config_path = test_dir / "hybrid.yaml"
    config_path.write_text(
        "\n".join(
            [
                "name: test_hybrid",
                "retriever: hybrid_rrf",
                "collection_name: test_collection",
                f"docs_dir: {docs_dir.as_posix()}",
                "embedding:",
                "  provider: hash",
                "  dimensions: 8",
                "chunking:",
                "  chunk_size: 200",
                "  overlap: 20",
                "ranking:",
                "  top_n: 3",
                "  rrf_k: 60",
            ]
        ),
        encoding="utf-8",
    )

    def fake_query_documents(**kwargs):
        return [
            RetrievedDocument(
                content="Redis READONLY replica",
                metadata={"source": source.as_posix(), "chunk_index": 0},
                score=0.9,
            )
        ]

    monkeypatch.setattr(hybrid_retriever, "query_documents", fake_query_documents)

    results = hybrid_retriever.retrieve_hybrid_documents("READONLY", top_k=1, config_path=config_path)

    assert results
    metadata = results[0].metadata
    assert metadata["source"] == source.as_posix()
    assert metadata["chunk_index"] == 0
    assert metadata["retrieval_method"]
    assert metadata["dense_rank"] == 1
    assert metadata["bm25_rank"] == 1
    assert metadata["rrf_score"] > 0
