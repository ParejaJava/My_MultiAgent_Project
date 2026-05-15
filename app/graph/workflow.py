"""LangGraph workflow orchestration."""

import re
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.diagnosis import infer_root_causes
from app.agents.intent import extract_intent
from app.agents.log_analysis import analyze_logs
from app.agents.retrieval import retrieve_evidence
from app.agents.solution import generate_report
from app.graph.state import WorkflowState, create_initial_state
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse, FaultContext


def intent_agent(state: WorkflowState) -> dict[str, Any]:
    """Input: user_question. Output: intent with system, symptom, error_codes, time_range, severity."""
    intent = extract_intent(state["user_question"])
    intent_data = intent.model_dump()
    existing_system = state.get("intent", {}).get("system")
    if existing_system:
        intent_data["system"] = existing_system
    return {"intent": intent_data, "last_agent": "intent_agent"}


def retrieval_agent(state: WorkflowState) -> dict[str, Any]:
    """Input: intent and user_question. Output: retrieved_docs document snippets with source metadata."""
    context = _context_from_state(state)
    return {"retrieved_docs": retrieve_evidence(context), "last_agent": "retrieval_agent"}


def log_analysis_agent(state: WorkflowState) -> dict[str, Any]:
    """Input: log_text. Output: log_findings deterministic log pattern findings."""
    return {"log_findings": analyze_logs(state["log_text"]), "last_agent": "log_analysis_agent"}


def diagnosis_agent(state: WorkflowState) -> dict[str, Any]:
    """Input: intent, retrieved_docs, log_findings. Output: root_causes."""
    context = _context_from_state(state)
    evidence = state["retrieved_docs"] + state["log_findings"]
    return {"root_causes": infer_root_causes(context, evidence), "last_agent": "diagnosis_agent"}


def solution_agent(state: WorkflowState) -> dict[str, str]:
    """Input: root_causes, retrieved_docs, log_findings. Output: solution and final_report."""
    solution = "Review the listed evidence and validate the likely root causes."
    final_report = generate_report(
        state["root_causes"],
        state["retrieved_docs"],
        state["log_findings"],
    )
    return {
        "solution": solution,
        "final_report": final_report,
        "workflow_status": "completed",
        "last_agent": "solution_agent",
    }


def supervisor_agent(state: WorkflowState) -> dict[str, str]:
    """Input: full workflow state. Output: next_agent routing decision and workflow_status."""
    next_agent = _select_next_agent(state)
    status = "completed" if next_agent == END else state["workflow_status"]
    return {"next_agent": next_agent, "workflow_status": status}


def fallback_answer(state: WorkflowState) -> dict[str, Any]:
    """Input: user_question, log_text, retrieved_docs. Output: fallback final_report."""
    log_findings = state["log_findings"] or analyze_logs(state["log_text"])
    root_causes = ["Insufficient evidence to infer a specific root cause."]
    report = generate_report(root_causes, [], log_findings)
    if "Fallback" not in report:
        report = f"{report}\nFallback: no retrieved knowledge base evidence was found."
    return {
        "log_findings": log_findings,
        "root_causes": root_causes,
        "solution": "Ask for more context or ingest relevant knowledge base documents.",
        "final_report": report,
        "workflow_status": "fallback_answer",
        "last_agent": "fallback_answer",
    }


def clarification_needed(state: WorkflowState) -> dict[str, str | list[str]]:
    """Input: user_question and intent. Output: clarification request final_report."""
    report = (
        "Clarification needed: please provide the affected system, observed symptom, "
        "error codes, time range, or relevant logs."
    )
    return {
        "root_causes": [],
        "solution": "Collect more incident details before diagnosis.",
        "final_report": report,
        "workflow_status": "clarification_needed",
        "last_agent": "clarification_needed",
    }


def build_workflow_graph() -> Any:
    """Build the Supervisor-routed LangGraph workflow."""
    graph = StateGraph(WorkflowState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("intent_agent", intent_agent)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("log_analysis_agent", log_analysis_agent)
    graph.add_node("diagnosis_agent", diagnosis_agent)
    graph.add_node("solution_agent", solution_agent)
    graph.add_node("fallback_answer", fallback_answer)
    graph.add_node("clarification_needed", clarification_needed)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "intent_agent": "intent_agent",
            "retrieval_agent": "retrieval_agent",
            "log_analysis_agent": "log_analysis_agent",
            "diagnosis_agent": "diagnosis_agent",
            "solution_agent": "solution_agent",
            "fallback_answer": "fallback_answer",
            "clarification_needed": "clarification_needed",
            END: END,
        },
    )
    graph.add_edge("intent_agent", "supervisor")
    graph.add_edge("retrieval_agent", "supervisor")
    graph.add_edge("log_analysis_agent", "supervisor")
    graph.add_edge("diagnosis_agent", "supervisor")
    graph.add_edge("solution_agent", END)
    graph.add_edge("fallback_answer", END)
    graph.add_edge("clarification_needed", END)
    return graph.compile()


def run_workflow(request: DiagnosisRequest) -> DiagnosisResponse:
    """Run the full LangGraph diagnosis workflow."""
    initial_state = create_initial_state(
        user_question=request.description,
        log_text=request.logs or "",
    )
    if request.service:
        initial_state["intent"] = {"system": request.service}

    final_state = workflow_graph.invoke(initial_state)

    return DiagnosisResponse(
        service=final_state["intent"].get("system"),
        root_causes=final_state["root_causes"],
        evidence=final_state["retrieved_docs"],
        log_findings=final_state["log_findings"],
        report=final_state["final_report"],
    )


def _context_from_state(state: WorkflowState) -> FaultContext:
    intent = state["intent"]
    symptom = intent.get("symptom") or state["user_question"]
    return FaultContext(
        service=intent.get("system"),
        description=symptom,
        logs=state["log_text"],
    )


def _route_from_supervisor(state: WorkflowState) -> str:
    return state["next_agent"]


def _select_next_agent(state: WorkflowState) -> str:
    last_agent = state["last_agent"]
    if last_agent == "":
        return "intent_agent"
    if last_agent == "intent_agent":
        if _needs_clarification(state):
            return "clarification_needed"
        return "retrieval_agent"
    if last_agent == "retrieval_agent":
        if not state["retrieved_docs"]:
            return "fallback_answer"
        if state["log_text"].strip():
            return "log_analysis_agent"
        return "diagnosis_agent"
    if last_agent == "log_analysis_agent":
        return "diagnosis_agent"
    if last_agent == "diagnosis_agent":
        return "solution_agent"
    return END


def _needs_clarification(state: WorkflowState) -> bool:
    intent = state["intent"]
    question = state["user_question"]
    tokens = re.findall(r"[a-zA-Z0-9_]+", question.lower())
    has_structured_clue = bool(
        intent.get("system")
        or intent.get("error_codes")
        or intent.get("time_range")
        or state["log_text"].strip()
    )
    return len(tokens) <= 1 and not has_structured_clue


workflow_graph = build_workflow_graph()
