from types import ModuleType
import sys

import pytest

from app.rag.config import get_collection_name, load_rag_config
from app.rag.embeddings import BGEFlagEmbeddingFunction, HashEmbeddingFunction, create_embedding_function


def test_hash_provider_creates_chroma_embedding_function() -> None:
    embedding = create_embedding_function(
        {
            "embedding": {
                "provider": "hash",
                "dimensions": 8,
            }
        }
    )

    assert isinstance(embedding, HashEmbeddingFunction)
    assert len(embedding(["redis timeout"])[0]) == 8


def test_invalid_provider_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        create_embedding_function({"embedding": {"provider": "unknown"}})


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_embedding_function({"embedding": {"provider": "openai"}})


def test_bge_local_provider_uses_flag_model(monkeypatch: pytest.MonkeyPatch) -> None:
    model_holder: dict[str, FakeFlagModel] = {}

    def build_flag_model(model_name: str, **kwargs) -> "FakeFlagModel":
        model = FakeFlagModel(model_name, kwargs)
        model_holder["model"] = model
        return model

    flag_embedding_module = ModuleType("FlagEmbedding")
    flag_embedding_module.FlagModel = build_flag_model

    monkeypatch.setitem(sys.modules, "FlagEmbedding", flag_embedding_module)
    monkeypatch.delenv("HF_HOME", raising=False)

    embedding = create_embedding_function(
        {
            "embedding": {
                "provider": "bge_local",
                "model": "BAAI/bge-base-zh-v1.5",
                "cache_folder": "D:/AgentData/ModelCache",
                "normalize_embeddings": True,
                "max_length": 128,
                "batch_size": 2,
                "use_fp16": True,
                "devices": ["cuda:0"],
            }
        }
    )

    vectors = embedding(["Redis timeout"])

    assert isinstance(embedding, BGEFlagEmbeddingFunction)
    assert model_holder["model"].model_name == "BAAI/bge-base-zh-v1.5"
    assert model_holder["model"].kwargs == {
        "normalize_embeddings": True,
        "use_fp16": True,
        "devices": ["cuda:0"],
    }
    assert model_holder["model"].encode_calls == [
        {
            "texts": ["Redis timeout"],
            "batch_size": 2,
            "max_length": 128,
        }
    ]
    assert [list(vector) for vector in vectors] == [[1.0, 2.0, 3.0]]


def test_rag_config_can_be_read() -> None:
    config = load_rag_config("configs/rag/baseline_hash.yaml")

    assert config["name"] == "baseline_hash"
    assert config["embedding"]["provider"] == "hash"
    assert get_collection_name(config) == "ops_knowledge_base_hash"


def test_bge_config_uses_base_zh_model() -> None:
    config = load_rag_config("configs/rag/bge_local.yaml")

    assert config["embedding"]["provider"] == "bge_local"
    assert config["embedding"]["model"] == "D:/AgentData/Models/bge-base-zh-v1.5"
    assert get_collection_name(config) == "ops_knowledge_base_bge_base_zh_v15"


def test_hybrid_bge_config_uses_same_dense_embedding_space() -> None:
    dense_config = load_rag_config("configs/rag/bge_local.yaml")
    hybrid_config = load_rag_config("configs/rag/hybrid_bge_rrf.yaml")

    assert hybrid_config["retriever"] == "hybrid_rrf"
    assert hybrid_config["embedding"]["provider"] == "bge_local"
    assert hybrid_config["embedding"]["model"] == dense_config["embedding"]["model"]
    assert get_collection_name(hybrid_config) == get_collection_name(dense_config)


class FakeFlagModel:
    def __init__(self, model_name: str, kwargs: dict[str, object]) -> None:
        self.model_name = model_name
        self.kwargs = kwargs
        self.encode_calls: list[dict[str, object]] = []

    def encode(self, texts: list[str], batch_size: int, max_length: int) -> list[list[float]]:
        self.encode_calls.append(
            {
                "texts": texts,
                "batch_size": batch_size,
                "max_length": max_length,
            }
        )
        return [[1.0, 2.0, 3.0] for _ in texts]
