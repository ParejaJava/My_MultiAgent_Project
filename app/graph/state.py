"""LangGraph workflow state definitions."""

from typing import Any, TypedDict


class WorkflowState(TypedDict):
    """State passed between LangGraph workflow nodes."""

    user_question: str
    log_text: str
    intent: dict[str, Any]
    retrieved_docs: list[str]
    log_findings: list[str]
    root_causes: list[str]
    solution: str
    final_report: str


def create_initial_state(user_question: str = "", log_text: str = "") -> WorkflowState:
    """Create a complete initial workflow state."""
    return {
        "user_question": user_question,
        "log_text": log_text,
        "intent": {},
        "retrieved_docs": [],
        "log_findings": [],
        "root_causes": [],
        "solution": "",
        "final_report": "",
    }
