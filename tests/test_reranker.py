import builtins
import os
from types import SimpleNamespace

import pytest

from app.rag.reranker import create_reranker, rerank_documents
from app.rag.vector_store import RetrievedDocument


def test_none_reranker_preserves_order() -> None:
    documents = [
        RetrievedDocument(content="first", metadata={"source": "a.md", "chunk_index": 0}),
        RetrievedDocument(content="second", metadata={"source": "b.md", "chunk_index": 0}),
    ]

    results = rerank_documents("query", documents, {"reranker": {"provider": "none"}})

    assert [document.content for document in results] == ["first", "second"]


def test_none_reranker_writes_rank_metadata() -> None:
    documents = [
        RetrievedDocument(content="first", metadata={"source": "a.md", "chunk_index": 0}),
        RetrievedDocument(content="second", metadata={"source": "b.md", "chunk_index": 0}),
    ]

    results = rerank_documents("query", documents, {"reranker": {"provider": "none"}})

    assert results[0].metadata["original_rank"] == 1
    assert results[0].metadata["final_rank"] == 1
    assert results[0].metadata["rerank_score"] is None
    assert results[1].metadata["original_rank"] == 2
    assert results[1].metadata["final_rank"] == 2


def test_reranker_interface_output_structure() -> None:
    document = RetrievedDocument(
        content="redis readonly",
        metadata={"source": "redis.md", "chunk_index": 1, "rrf_score": 0.1},
        score=0.1,
    )

    results = rerank_documents("readonly", [document], {"reranker": {"provider": "none"}})

    assert isinstance(results[0], RetrievedDocument)
    assert results[0].content == "redis readonly"
    assert results[0].metadata["source"] == "redis.md"
    assert results[0].metadata["chunk_index"] == 1
    assert "original_rank" in results[0].metadata
    assert "final_rank" in results[0].metadata
    assert "rerank_score" in results[0].metadata


def test_bge_provider_missing_flagembedding_has_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "FlagEmbedding":
            raise ModuleNotFoundError("No module named 'FlagEmbedding'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="FlagEmbedding is required"):
        create_reranker({"reranker": {"provider": "bge"}})


def test_bge_flag_reranker_reranks_by_score(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeFlagReranker:
        def __init__(self, model: str, **kwargs) -> None:
            self.model = model
            self.kwargs = kwargs

        def compute_score(self, pairs, batch_size: int = 16):
            assert self.model == "BAAI/bge-reranker-base"
            assert self.kwargs["query_max_length"] == 256
            assert self.kwargs["use_fp16"] is True
            assert self.kwargs["devices"] == ["cuda:1"]
            assert batch_size == 2
            assert pairs[0] == ["redis readonly", "mysql lock wait"]
            return [0.1 if "mysql" in pair[1] else 0.9 for pair in pairs]

    monkeypatch.setitem(
        __import__("sys").modules,
        "FlagEmbedding",
        SimpleNamespace(FlagReranker=FakeFlagReranker),
    )
    monkeypatch.delenv("HF_HOME", raising=False)
    documents = [
        RetrievedDocument(content="mysql lock wait", metadata={"source": "mysql.md"}),
        RetrievedDocument(content="redis readonly replica", metadata={"source": "redis.md"}),
    ]

    results = rerank_documents(
        "redis readonly",
        documents,
        {
            "reranker": {
                "provider": "bge",
                "model": "BAAI/bge-reranker-base",
                "cache_folder": "D:/AgentData/ModelCache",
                "devices": ["cuda:1"],
                "batch_size": 2,
            }
        },
    )

    assert [document.metadata["source"] for document in results] == ["redis.md", "mysql.md"]
    assert results[0].metadata["original_rank"] == 2
    assert results[0].metadata["final_rank"] == 1
    assert results[0].metadata["rerank_score"] == 0.9
    assert os.environ["HF_HOME"] == "D:/AgentData/ModelCache"


def test_invalid_reranker_provider_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unsupported reranker provider"):
        create_reranker({"reranker": {"provider": "mystery"}})
