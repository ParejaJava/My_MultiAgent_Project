"""LangGraph workflow state definitions."""

from typing import Any, TypedDict

from app.graph.session import ensure_session_id, load_session_history


class WorkflowState(TypedDict):
    """State passed between LangGraph workflow nodes."""

    session_id: str
    conversation_history: list[dict[str, str]]
    user_question: str
    normalized_question: str
    log_text: str
    intent: dict[str, Any]
    route: str
    next_agent: str
    last_agent: str
    workflow_status: str
    clarification_question: str | None
    retrieved_docs: list[str]
    evidence_items: list[dict[str, Any]]
    agent_steps: list[dict[str, Any]]
    dialogue_observations: list[str]
    operations_plan: list[str]
    completed_steps: list[str]
    remaining_steps: list[str]
    replan_reason: str | None
    log_findings: list[str]
    root_causes: list[str]
    solution: str
    final_report: str
    final_answer: str


def create_initial_state(
    user_question: str = "",
    log_text: str = "",
    service: str | None = None,
    session_id: str | None = None,
) -> WorkflowState:
    """Create a complete initial workflow state."""
    resolved_session_id = ensure_session_id(session_id)
    return {
        "session_id": resolved_session_id,
        "conversation_history": load_session_history(resolved_session_id),
        "user_question": user_question,
        "normalized_question": user_question,
        "log_text": log_text,
        "intent": {"system": service} if service else {},
        "route": "",
        "next_agent": "supervisor",
        "last_agent": "",
        "workflow_status": "running",
        "clarification_question": None,
        "retrieved_docs": [],
        "evidence_items": [],
        "agent_steps": [],
        "dialogue_observations": [],
        "operations_plan": [],
        "completed_steps": [],
        "remaining_steps": [],
        "replan_reason": None,
        "log_findings": [],
        "root_causes": [],
        "solution": "",
        "final_report": "",
        "final_answer": "",
    }
