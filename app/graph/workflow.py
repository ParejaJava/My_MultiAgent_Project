"""Minimal workflow orchestration."""

from app.agents.diagnosis import infer_root_causes
from app.agents.intent import extract_fault_context
from app.agents.log_analysis import analyze_logs
from app.agents.retrieval import retrieve_evidence
from app.agents.solution import generate_report
from app.graph.state import create_initial_state
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse


def run_workflow(request: DiagnosisRequest) -> DiagnosisResponse:
    """Run a simple sequential workflow."""
    state = create_initial_state(
        user_question=request.description,
        log_text=request.logs or "",
    )
    context = extract_fault_context(request)
    state["intent"] = context.model_dump()
    state["retrieved_docs"] = retrieve_evidence(context)
    state["log_findings"] = analyze_logs(state["log_text"])
    state["root_causes"] = infer_root_causes(
        context,
        state["retrieved_docs"] + state["log_findings"],
    )
    state["solution"] = "Review the listed evidence and validate the likely root causes."
    state["final_report"] = generate_report(
        state["root_causes"],
        state["retrieved_docs"],
        state["log_findings"],
    )

    return DiagnosisResponse(
        service=context.service,
        root_causes=state["root_causes"],
        evidence=state["retrieved_docs"],
        log_findings=state["log_findings"],
        report=state["final_report"],
    )
