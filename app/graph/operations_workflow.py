"""Plan-execute-replan operations sub-workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.operations import (
    build_default_plan,
    execute_diagnosis,
    execute_intent,
    execute_log_analysis,
    execute_retrieval,
    execute_solution,
    operation_step,
    request_replan,
    should_replan,
)


class OperationsState(TypedDict):
    """State for the operations plan-execute-replan subgraph."""

    user_question: str
    log_text: str
    service: str | None
    intent: dict[str, Any]
    evidence_items: list[dict[str, Any]]
    retrieved_docs: list[str]
    log_findings: list[str]
    root_causes: list[str]
    solution: str
    final_report: str
    final_answer: str
    operations_plan: list[str]
    completed_steps: list[str]
    remaining_steps: list[str]
    current_step: str
    replan_reason: str | None
    agent_steps: list[dict[str, Any]]
    workflow_status: str


def run_operations_workflow(
    user_question: str,
    log_text: str = "",
    service: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run the operations plan-execute-replan graph."""
    initial_state: OperationsState = {
        "user_question": user_question,
        "log_text": log_text,
        "service": service,
        "intent": {},
        "evidence_items": [],
        "retrieved_docs": [],
        "log_findings": [],
        "root_causes": [],
        "solution": "",
        "final_report": "",
        "final_answer": "",
        "operations_plan": [],
        "completed_steps": [],
        "remaining_steps": [],
        "current_step": "",
        "replan_reason": None,
        "agent_steps": [],
        "workflow_status": "running",
    }
    result = operations_graph.invoke(initial_state, config={"configurable": {"top_k": top_k}})
    return {
        "intent": result["intent"],
        "evidence_items": result["evidence_items"],
        "retrieved_docs": result["retrieved_docs"],
        "log_findings": result["log_findings"],
        "root_causes": result["root_causes"],
        "solution": result["solution"],
        "final_report": result["final_report"],
        "final_answer": result["final_answer"],
        "operations_plan": result["operations_plan"],
        "completed_steps": result["completed_steps"],
        "remaining_steps": result["remaining_steps"],
        "replan_reason": result["replan_reason"],
        "agent_steps": result["agent_steps"],
        "workflow_status": result["workflow_status"],
    }


def plan_node(state: OperationsState) -> dict[str, Any]:
    """Create the deterministic default operations plan."""
    plan = build_default_plan(state["log_text"])
    return {
        "operations_plan": plan,
        "remaining_steps": plan,
        "agent_steps": state["agent_steps"]
        + [operation_step("operations", "plan", "completed", f"Planned steps: {', '.join(plan)}")],
    }


def execute_step_node(state: OperationsState) -> dict[str, Any]:
    """Execute one allowed operations step."""
    if not state["remaining_steps"]:
        return {}
    current_step = state["remaining_steps"][0]
    remaining_steps = state["remaining_steps"][1:]
    updates: dict[str, Any] = {
        "current_step": current_step,
        "remaining_steps": remaining_steps,
        "completed_steps": state["completed_steps"] + [current_step],
    }
    if current_step == "intent":
        updates.update(execute_intent(state["user_question"], service=state["service"]))
        observation = "Intent extracted."
        sources: list[str] = []
    elif current_step == "retrieval":
        updates.update(execute_retrieval(state["user_question"]))
        sources = [item.get("source", "unknown") for item in updates.get("evidence_items", [])]
        observation = f"Retrieved {len(updates.get('retrieved_docs', []))} evidence items."
    elif current_step == "log_analysis":
        updates.update(execute_log_analysis(state["log_text"]))
        observation = f"Found {len(updates.get('log_findings', []))} log findings."
        sources = []
    elif current_step == "diagnosis":
        updates.update(execute_diagnosis(state["intent"], state["retrieved_docs"], state["log_findings"]))
        observation = f"Inferred {len(updates.get('root_causes', []))} root causes."
        sources = []
    elif current_step == "solution":
        updates.update(execute_solution(state["root_causes"], state["retrieved_docs"], state["log_findings"]))
        observation = "Generated operations report."
        sources = []
    else:
        observation = f"Skipped unsupported step: {current_step}."
        sources = []

    updates["agent_steps"] = state["agent_steps"] + [
        operation_step("operations", current_step, "completed", observation, sources)
    ]
    return updates


def evaluate_node(state: OperationsState) -> dict[str, Any]:
    """Evaluate whether the plan needs rework."""
    reason = should_replan(state)
    if reason:
        return {
            "replan_reason": reason,
            "agent_steps": state["agent_steps"]
            + [operation_step("operations", "evaluate", "needs_replan", reason)],
        }
    return {
        "replan_reason": None,
        "agent_steps": state["agent_steps"]
        + [operation_step("operations", "evaluate", "completed", "No replan needed.")],
    }


def replan_or_finish_node(state: OperationsState) -> dict[str, Any]:
    """Either add constrained replan steps or prepare to finish."""
    if state["replan_reason"]:
        replan_steps = normalize_replan_steps(request_replan(state), state)
        return {
            "remaining_steps": replan_steps,
            "operations_plan": state["operations_plan"] + replan_steps,
            "replan_reason": None,
            "agent_steps": state["agent_steps"]
            + [operation_step("operations", "replan", "completed", f"Added steps: {', '.join(replan_steps)}")],
        }
    return {}


def normalize_replan_steps(replan_steps: list[str], state: OperationsState) -> list[str]:
    """Keep replans executable by adding required predecessor steps."""
    normalized: list[str] = []
    for step in replan_steps:
        if step == "solution" and not state["root_causes"] and "diagnosis" not in normalized:
            normalized.append("diagnosis")
        if step not in normalized:
            normalized.append(step)
    return normalized or ["diagnosis", "solution"]


def synthesize_node(state: OperationsState) -> dict[str, Any]:
    """Finalize the operations result."""
    final_report = state["final_report"]
    if not final_report:
        final_report = execute_solution(state["root_causes"], state["retrieved_docs"], state["log_findings"])["final_report"]
    status = "completed" if state["retrieved_docs"] or state["log_findings"] else "fallback_answer"
    return {
        "final_report": final_report,
        "final_answer": final_report,
        "workflow_status": status,
        "agent_steps": state["agent_steps"]
        + [operation_step("operations", "synthesize", "completed", "Operations workflow finalized.")],
    }


def route_after_evaluate(state: OperationsState) -> str:
    """Route after evaluation."""
    if state["replan_reason"]:
        return "replan_or_finish"
    if state["remaining_steps"]:
        return "execute_step"
    return "synthesize"


def route_after_replan(state: OperationsState) -> str:
    """Route after replanning."""
    if state["remaining_steps"]:
        return "execute_step"
    return "synthesize"


def build_operations_graph() -> Any:
    """Build the operations plan-execute-replan graph."""
    graph = StateGraph(OperationsState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute_step", execute_step_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("replan_or_finish", replan_or_finish_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute_step")
    graph.add_edge("execute_step", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "execute_step": "execute_step",
            "replan_or_finish": "replan_or_finish",
            "synthesize": "synthesize",
        },
    )
    graph.add_conditional_edges(
        "replan_or_finish",
        route_after_replan,
        {
            "execute_step": "execute_step",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("synthesize", END)
    return graph.compile()


operations_graph = build_operations_graph()
