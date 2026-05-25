"""LangGraph workflow orchestration."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.dialogue import build_clarification_question, normalize_question
from app.agents.supervisor import select_route
from app.graph.dialogue_workflow import run_dialogue_workflow
from app.graph.operations_workflow import run_operations_workflow
from app.graph.session import append_session_turn, load_session_history
from app.graph.state import WorkflowState, create_initial_state
from app.schemas.diagnosis import AgentStep, DiagnosisRequest, DiagnosisResponse, EvidenceItem


def supervisor_agent(state: WorkflowState) -> dict[str, str]:
    """Route to the next top-level agent without doing diagnosis work."""
    route = select_route(state)
    next_agent = {
        "dialogue": "dialogue_agent",
        "operations": "operations_agent",
        "clarification": "clarification_agent",
        "final": "final_agent",
    }[route]
    return {"route": route, "next_agent": next_agent, "last_agent": "supervisor_agent"}


def dialogue_agent(state: WorkflowState) -> dict[str, Any]:
    """Handle lightweight conversation with a ReAct sub-workflow."""
    result = run_dialogue_workflow(state)
    return {
        **result,
        "last_agent": "dialogue_agent",
    }


def clarification_agent(state: WorkflowState) -> dict[str, Any]:
    """Ask for missing information before operations diagnosis."""
    question = build_clarification_question(state["user_question"])
    return {
        "clarification_question": question,
        "final_answer": question,
        "final_report": question,
        "workflow_status": "clarification_needed",
        "last_agent": "clarification_agent",
    }


def operations_agent(state: WorkflowState) -> dict[str, Any]:
    """Run the operations plan-execute-replan sub-workflow."""
    service = state.get("intent", {}).get("system")
    normalized_question = normalize_question(state["user_question"], service=service)
    result = run_operations_workflow(
        normalized_question,
        log_text=state["log_text"],
        service=service,
    )
    return {
        **result,
        "normalized_question": normalized_question,
        "last_agent": "operations_agent",
    }


def final_agent(state: WorkflowState) -> dict[str, Any]:
    """Finalize the response and persist lightweight session history."""
    final_answer = state["final_answer"] or state["final_report"]
    append_session_turn(state["session_id"], state["user_question"], final_answer)
    return {
        "conversation_history": load_session_history(state["session_id"]),
        "final_answer": final_answer,
        "last_agent": "final_agent",
        "next_agent": END,
    }


def build_workflow_graph() -> Any:
    """Build the supervisor-routed LangGraph workflow."""
    graph = StateGraph(WorkflowState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("dialogue_agent", dialogue_agent)
    graph.add_node("operations_agent", operations_agent)
    graph.add_node("clarification_agent", clarification_agent)
    graph.add_node("final_agent", final_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "dialogue_agent": "dialogue_agent",
            "operations_agent": "operations_agent",
            "clarification_agent": "clarification_agent",
            "final_agent": "final_agent",
        },
    )
    graph.add_edge("dialogue_agent", "final_agent")
    graph.add_edge("operations_agent", "final_agent")
    graph.add_edge("clarification_agent", "final_agent")
    graph.add_edge("final_agent", END)
    return graph.compile()


def run_workflow(request: DiagnosisRequest) -> DiagnosisResponse:
    """Run the full LangGraph diagnosis workflow."""
    initial_state = create_initial_state(
        user_question=request.description,
        log_text=request.logs or "",
        service=request.service,
        session_id=request.session_id,
    )
    final_state = workflow_graph.invoke(initial_state)
    evidence_items = [
        EvidenceItem.model_validate(item)
        for item in final_state.get("evidence_items", [])
    ]
    agent_steps = [
        AgentStep.model_validate(item)
        for item in final_state.get("agent_steps", [])
    ]
    route = str(final_state.get("route", ""))
    return DiagnosisResponse(
        session_id=str(final_state["session_id"]),
        route=route,
        needs_clarification=route == "clarification",
        clarification_question=final_state.get("clarification_question"),
        service=final_state.get("intent", {}).get("system"),
        root_causes=final_state["root_causes"],
        evidence=final_state["retrieved_docs"],
        evidence_items=evidence_items,
        agent_steps=agent_steps,
        log_findings=final_state["log_findings"],
        report=final_state["final_report"],
    )


def _route_from_supervisor(state: WorkflowState) -> str:
    return state["next_agent"]


workflow_graph = build_workflow_graph()
