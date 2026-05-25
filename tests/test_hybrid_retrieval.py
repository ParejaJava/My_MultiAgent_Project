from pathlib import Path
from types import SimpleNamespace
import sys

from app.config import project_relative_source, resolve_project_path
from app.rag.bm25_store import BM25Store, build_index_fingerprint, load_markdown_document_records, search_bm25_documents, tokenize
import app.rag.bm25_store as bm25_store
from app.rag.fusion import reciprocal_rank_fusion
import app.rag.hybrid_retriever as hybrid_retriever
from app.rag.config import load_rag_config
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


def test_bm25_retrieves_keyword(monkeypatch, tmp_path: Path) -> None:
    install_fake_jieba(monkeypatch)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "mysql.md"
    source.write_text("MySQL error 1205 Lock wait timeout exceeded.", encoding="utf-8")

    results = search_bm25_documents(
        "1205",
        top_n=3,
        docs_dir=docs_dir,
        chunk_size=200,
        overlap=20,
        index_directory=tmp_path / "bm25",
    )

    assert results
    assert results[0].metadata["source"] == project_relative_source(source)
    assert results[0].metadata["retrieval_method"] == "bm25"
    assert results[0].metadata["bm25_rank"] == 1


def test_bm25_uses_jieba_for_chinese_tokens(monkeypatch) -> None:
    calls: list[str] = []

    def fake_lcut(text: str) -> list[str]:
        calls.append(text)
        return ["长", "事务"]

    monkeypatch.setitem(sys.modules, "jieba", SimpleNamespace(lcut=fake_lcut))

    assert tokenize("MySQL 长事务 1205") == ["mysql", "长", "事务", "1205"]
    assert calls == ["长事务"]


def test_bm25_loads_project_jieba_user_dict(monkeypatch) -> None:
    loaded_paths: list[str] = []

    def fake_load_userdict(path: str) -> None:
        loaded_paths.append(Path(path).as_posix())

    monkeypatch.setitem(
        sys.modules,
        "jieba",
        SimpleNamespace(lcut=lambda text: [text], load_userdict=fake_load_userdict),
    )
    bm25_store._LOADED_USER_DICTS.clear()

    assert tokenize("Redis主从切换") == ["redis", "主从切换"]
    assert loaded_paths == [resolve_project_path("configs/jieba/userdict.txt").as_posix()]


def test_hybrid_configs_define_jieba_user_dict() -> None:
    for config_path in (
        "configs/rag/hybrid_hash_rrf.yaml",
        "configs/rag/hybrid_bge_rrf.yaml",
        "configs/rag/hybrid_rrf_rerank.yaml",
    ):
        config = load_rag_config(config_path)

        assert config["bm25"]["tokenizer"] == "jieba"
        assert config["bm25"]["user_dict"] == "configs/jieba/userdict.txt"
        assert config["bm25"]["index_directory"] == "D:/AgentData/BM25Store"


def test_bm25_persists_and_reuses_chunk_index(monkeypatch, tmp_path: Path) -> None:
    install_fake_jieba(monkeypatch)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "ops.md").write_text("alpha beta gamma", encoding="utf-8")
    index_directory = tmp_path / "bm25"

    first_results = search_bm25_documents(
        "alpha",
        docs_dir=docs_dir,
        index_directory=index_directory,
        chunk_size=100,
        overlap=10,
    )
    index_files = list(index_directory.glob("*.json"))
    assert first_results
    assert len(index_files) == 1

    def fail_from_documents(*args, **kwargs):
        raise AssertionError("BM25 index should be loaded from disk")

    monkeypatch.setattr(BM25Store, "from_documents", classmethod(fail_from_documents))
    second_results = search_bm25_documents(
        "alpha",
        docs_dir=docs_dir,
        index_directory=index_directory,
        chunk_size=100,
        overlap=10,
    )

    assert second_results
    assert len(list(index_directory.glob("*.json"))) == 1


def test_bm25_indexes_chunks_not_whole_documents(monkeypatch, tmp_path: Path) -> None:
    install_fake_jieba(monkeypatch)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "chunks.md"
    source.write_text(("a" * 40) + " target-token", encoding="utf-8")

    results = search_bm25_documents(
        "target-token",
        docs_dir=docs_dir,
        index_directory=tmp_path / "bm25",
        chunk_size=30,
        overlap=0,
    )

    assert results
    assert results[0].metadata["source"] == project_relative_source(source)
    assert results[0].metadata["chunk_index"] == 1


def test_bm25_fingerprint_changes_with_chunking_strategy(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "ops.md").write_text("# Redis\n\n## READONLY\n\nReplica write issue.", encoding="utf-8")
    documents = load_markdown_document_records(docs_dir)

    character_fingerprint = build_index_fingerprint(
        documents=documents,
        docs_dir=docs_dir,
        docs_dirs=None,
        chunk_size=100,
        overlap=10,
        chunking_strategy="character",
        k1=1.5,
        b=0.75,
        user_dict=None,
    )
    markdown_fingerprint = build_index_fingerprint(
        documents=documents,
        docs_dir=docs_dir,
        docs_dirs=None,
        chunk_size=100,
        overlap=10,
        chunking_strategy="markdown",
        k1=1.5,
        b=0.75,
        user_dict=None,
    )

    assert character_fingerprint != markdown_fingerprint


def test_hybrid_retriever_returns_required_metadata(monkeypatch, tmp_path: Path) -> None:
    install_fake_jieba(monkeypatch)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    source = docs_dir / "redis.md"
    source.write_text("Redis READONLY You can't write against a read only replica.", encoding="utf-8")
    config_path = tmp_path / "hybrid.yaml"
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
                "bm25:",
                f"  index_directory: {(tmp_path / 'bm25').as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    def fake_query_documents(**kwargs):
        return [
            RetrievedDocument(
                content="Redis READONLY replica",
                metadata={"source": project_relative_source(source), "chunk_index": 0},
                score=0.9,
            )
        ]

    monkeypatch.setattr(hybrid_retriever, "query_documents", fake_query_documents)

    results = hybrid_retriever.retrieve_hybrid_documents("READONLY", top_k=1, config_path=config_path)

    assert results
    metadata = results[0].metadata
    assert metadata["source"] == project_relative_source(source)
    assert metadata["chunk_index"] == 0
    assert metadata["retrieval_method"]
    assert metadata["dense_rank"] == 1
    assert metadata["bm25_rank"] == 1
    assert metadata["rrf_score"] > 0
    assert metadata["original_rank"] == 1
    assert metadata["final_rank"] == 1
    assert metadata["rerank_score"] is None


def install_fake_jieba(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "jieba", SimpleNamespace(lcut=lambda text: [text]))
