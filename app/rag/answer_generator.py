"""Generate diagnosis answers from retrieved RAG contexts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.providers import create_llm_provider
from app.rag.vector_store import RetrievedDocument


@dataclass(frozen=True)
class UsedContext:
    """A retrieved context passed to the LLM."""

    source: str
    chunk_index: int | None
    citation: str
    content: str


@dataclass(frozen=True)
class AnswerGenerationResult:
    """Structured answer generation output."""

    answer: str
    cited_sources: list[str]
    used_contexts: list[UsedContext]


SYSTEM_PROMPT = """你是一个运维故障诊断助手。
你只能基于用户提供的检索上下文回答。
不得编造检索上下文中没有的故障原因、命令或解决步骤。
如果上下文不足，必须明确说明“根据当前知识库无法确定”。
答案应包含：可能原因、排查步骤、解决方案。
必须保留 source 引用，引用格式为 [source: <source>#chunk_<chunk_index>] 或 [source: <source>]。
"""


def generate_answer(
    user_question: str,
    retrieved_documents: list[RetrievedDocument],
    config: dict[str, Any],
) -> AnswerGenerationResult:
    """Generate a diagnosis answer from retrieved documents."""
    used_contexts = build_used_contexts(retrieved_documents)
    cited_sources = [context.citation for context in used_contexts]
    if not used_contexts:
        return AnswerGenerationResult(
            answer=(
                "根据当前知识库无法确定。\n"
                "可能原因: 当前没有可用检索上下文。\n"
                "排查步骤: 请先补充错误码、日志片段、服务名称，或重新构建知识库索引。\n"
                "解决方案: 暂无足够依据给出确定方案。"
            ),
            cited_sources=[],
            used_contexts=[],
        )

    provider = create_llm_provider(config)
    user_prompt = build_user_prompt(user_question, used_contexts)
    answer = provider.generate(SYSTEM_PROMPT, user_prompt).strip()
    answer = ensure_citations(answer, cited_sources)
    return AnswerGenerationResult(answer=answer, cited_sources=cited_sources, used_contexts=used_contexts)


def build_used_contexts(retrieved_documents: list[RetrievedDocument]) -> list[UsedContext]:
    """Build contexts with stable citations from retrieved documents."""
    contexts: list[UsedContext] = []
    for document in retrieved_documents:
        source = str(document.metadata.get("source", "unknown"))
        raw_chunk_index = document.metadata.get("chunk_index")
        chunk_index = parse_chunk_index(raw_chunk_index)
        citation = format_source_citation(source, chunk_index)
        contexts.append(
            UsedContext(
                source=source,
                chunk_index=chunk_index,
                citation=citation,
                content=document.content,
            )
        )
    return contexts


def build_user_prompt(user_question: str, used_contexts: list[UsedContext]) -> str:
    """Build the user prompt with retrieved contexts."""
    context_text = "\n\n".join(
        f"{context.citation}\n{context.content}" for context in used_contexts
    )
    return (
        f"用户问题:\n{user_question}\n\n"
        f"检索上下文:\n{context_text}\n\n"
        "请基于以上上下文生成诊断答案，包含：可能原因、排查步骤、解决方案。"
    )


def format_source_citation(source: str, chunk_index: int | None = None) -> str:
    """Format a source citation."""
    if chunk_index is None:
        return f"[source: {source}]"
    return f"[source: {source}#chunk_{chunk_index}]"


def parse_chunk_index(value: object) -> int | None:
    """Parse a chunk index from metadata."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def ensure_citations(answer: str, cited_sources: list[str]) -> str:
    """Append citations if the provider omitted them."""
    missing = [citation for citation in cited_sources if citation not in answer]
    if not missing:
        return answer
    return f"{answer}\n\n引用来源: {' '.join(missing)}"
