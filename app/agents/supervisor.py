"""Supervisor agent routing rules."""

from __future__ import annotations

from typing import Any, Literal

from app.agents.dialogue import is_dialogue_message, is_faq_message, needs_clarification


Route = Literal["dialogue", "operations", "clarification", "final"]


def select_route(state: dict[str, Any]) -> Route:
    """Select the next top-level agent without performing diagnosis work."""
    last_agent = str(state.get("last_agent", ""))
    if last_agent in {"dialogue_agent", "operations_agent", "clarification_agent"}:
        return "final"

    user_question = str(state.get("user_question", ""))
    log_text = str(state.get("log_text", ""))
    intent = state.get("intent", {}) if isinstance(state.get("intent"), dict) else {}
    service = intent.get("system")

    if is_dialogue_message(user_question):
        return "dialogue"
    if is_faq_message(user_question):
        return "dialogue"
    if needs_clarification(user_question, service=service, logs=log_text):
        return "clarification"
    return "operations"


def route_next_step(step: str) -> str:
    """Backward-compatible route helper for older callers."""
    routes = {
        "intent": "retrieval",
        "retrieval": "log_analysis",
        "log_analysis": "diagnosis",
        "diagnosis": "solution",
    }
    return routes.get(step, "done")
