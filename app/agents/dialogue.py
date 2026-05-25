"""Dialogue agent helpers and ReAct actions."""

from __future__ import annotations

import re
from typing import Any

from app.rag.hybrid_retriever import retrieve_hybrid_documents
from app.rag.vector_store import RetrievedDocument


GREETING_MESSAGES = {"hi", "hello", "hey", "你好", "您好", "嗨"}
THANKS_MESSAGES = {"thanks", "thank you", "谢谢", "多谢"}
VAGUE_MESSAGES = {"help", "issue", "problem", "error", "故障", "问题", "报错", "帮忙"}
FAQ_KEYWORDS = {"what is", "是什么", "什么意思", "解释", "概念", "how does", "原理"}
DIAGNOSTIC_KEYWORDS = {"readonly", "timeout", "error", "failed", "down", "latency", "500", "503", "故障", "报错"}


def is_dialogue_message(user_question: str) -> bool:
    """Return whether the message is lightweight conversation rather than an incident."""
    normalized = user_question.strip().lower()
    return normalized in GREETING_MESSAGES or normalized in THANKS_MESSAGES


def is_faq_message(user_question: str) -> bool:
    """Return whether the message is a FAQ-style request suitable for dialogue RAG."""
    lowered = user_question.lower()
    return any(keyword in lowered for keyword in FAQ_KEYWORDS)


def is_diagnostic_message(user_question: str) -> bool:
    """Return whether a message appears to ask for incident diagnosis."""
    lowered = user_question.lower()
    return any(keyword in lowered for keyword in DIAGNOSTIC_KEYWORDS)


def needs_clarification(user_question: str, service: str | None = None, logs: str = "") -> bool:
    """Return whether the request lacks enough operational detail to diagnose."""
    normalized = user_question.strip().lower()
    if is_dialogue_message(user_question) or is_faq_message(user_question):
        return False
    if service or logs.strip():
        return False
    if normalized in VAGUE_MESSAGES:
        return True
    tokens = re.findall(r"[a-zA-Z0-9_]+", normalized)
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", user_question))
    if has_cjk:
        return len(user_question.strip()) <= 4
    return len(tokens) <= 1


def normalize_question(user_question: str, service: str | None = None) -> str:
    """Normalize a user question before operations diagnosis."""
    question = " ".join(user_question.split())
    if service and service.lower() not in question.lower():
        return f"{service} {question}".strip()
    return question


def choose_dialogue_action(user_question: str) -> str:
    """Choose the next ReAct action for dialogue."""
    if is_dialogue_message(user_question):
        return "respond"
    if is_faq_message(user_question):
        return "rag_lookup"
    if needs_clarification(user_question):
        return "clarify"
    return "normalize"


def observe_history(history: list[dict[str, str]]) -> str:
    """Summarize recent conversation history for the dialogue workflow."""
    if not history:
        return "No prior conversation history."
    return f"Loaded {len(history)} prior conversation messages."


def build_dialogue_response(user_question: str) -> str:
    """Return a lightweight conversation response."""
    normalized = user_question.strip().lower()
    if normalized in THANKS_MESSAGES:
        return "You are welcome. Share the affected service, error message, symptom, time range, or logs when ready."
    return "Hello. I can help with operations diagnosis. Please share the affected service, symptom, error, time range, or logs."


def build_clarification_question(user_question: str) -> str:
    """Ask for the minimum extra detail needed for diagnosis."""
    return (
        "Clarification needed: please provide the affected service, observed symptom, "
        "error code, time range, or relevant logs so I can run the operations diagnosis workflow."
    )


def lookup_dialogue_rag(query: str, top_k: int = 2) -> list[RetrievedDocument]:
    """Retrieve lightweight knowledge for FAQ-style dialogue responses."""
    return retrieve_hybrid_documents(query, top_k=top_k)


def build_faq_response(query: str, documents: list[RetrievedDocument]) -> tuple[str, list[str]]:
    """Build a bounded FAQ response from retrieved contexts."""
    if not documents:
        return (
            "I do not have enough knowledge-base context to answer that confidently. "
            "Please provide more detail or ask an operations diagnosis question.",
            [],
        )
    sources = [str(document.metadata.get("source", "unknown")) for document in documents]
    context = "\n".join(document.content for document in documents[:2])
    return (
        "Based on the knowledge base, here is the relevant concept summary:\n"
        f"{context}\n\n"
        "For incident diagnosis, please include the affected service, symptom, logs, and time range.",
        sources,
    )


def agent_step(agent: str, action: str, status: str, observation: str = "", sources: list[str] | None = None) -> dict[str, Any]:
    """Build a public agent step summary."""
    return {
        "agent": agent,
        "action": action,
        "status": status,
        "observation": observation,
        "sources": sources or [],
    }
