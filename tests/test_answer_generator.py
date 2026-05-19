import pytest

from app.llm.providers import create_llm_provider
from app.rag.answer_generator import format_source_citation, generate_answer
from app.rag.vector_store import RetrievedDocument


def test_mock_llm_generation_flow() -> None:
    documents = [
        RetrievedDocument(
            content="Redis READONLY 表示写请求打到了 replica。",
            metadata={"source": "data/docs/redis_ops_diagnosis.md", "chunk_index": 4},
        )
    ]

    result = generate_answer(
        "Redis READONLY 怎么处理？",
        documents,
        {"llm": {"provider": "mock"}},
    )

    assert "可能原因" in result.answer
    assert "排查步骤" in result.answer
    assert "解决方案" in result.answer
    assert "[source: data/docs/redis_ops_diagnosis.md#chunk_4]" in result.answer
    assert result.cited_sources == ["[source: data/docs/redis_ops_diagnosis.md#chunk_4]"]
    assert result.used_contexts[0].source == "data/docs/redis_ops_diagnosis.md"


def test_no_context_returns_insufficient_answer() -> None:
    result = generate_answer("这个问题怎么修？", [], {"llm": {"provider": "mock"}})

    assert "根据当前知识库无法确定" in result.answer
    assert result.cited_sources == []
    assert result.used_contexts == []


def test_source_citation_format() -> None:
    assert (
        format_source_citation("data/docs/mysql_ops_diagnosis.md", 2)
        == "[source: data/docs/mysql_ops_diagnosis.md#chunk_2]"
    )
    assert (
        format_source_citation("data/docs/mysql_ops_diagnosis.md")
        == "[source: data/docs/mysql_ops_diagnosis.md]"
    )


def test_kimi_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)

    with pytest.raises(ValueError, match="MOONSHOT_API_KEY"):
        create_llm_provider({"llm": {"provider": "kimi", "base_url": "https://api.moonshot.cn/v1"}})


def test_invalid_llm_provider_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_provider({"llm": {"provider": "unknown"}})
