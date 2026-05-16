import pytest

from app.rag.config import get_collection_name, load_rag_config
from app.rag.embeddings import HashEmbeddingFunction, create_embedding_function


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


def test_rag_config_can_be_read() -> None:
    config = load_rag_config("configs/rag/baseline_hash.yaml")

    assert config["name"] == "baseline_hash"
    assert config["embedding"]["provider"] == "hash"
    assert get_collection_name(config) == "ops_knowledge_base_hash"
