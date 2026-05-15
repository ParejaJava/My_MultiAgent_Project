import app.graph.workflow as workflow
from app.graph.state import create_initial_state
from app.graph.workflow import run_workflow
from app.schemas.diagnosis import DiagnosisRequest


def test_workflow_execution() -> None:
    response = run_workflow(
        DiagnosisRequest(
            service="checkout",
            description="timeout errors",
            logs="ERROR timeout from gateway",
        )
    )

    assert response.root_causes
    assert response.report
    assert response.log_findings


def test_workflow_fallback_behavior() -> None:
    response = run_workflow(DiagnosisRequest(description="unknown symptom"))

    assert response.root_causes == ["Insufficient evidence to infer a specific root cause."]
    assert "Fallback" in response.report


def test_supervisor_skips_log_analysis_when_no_logs(monkeypatch) -> None:
    monkeypatch.setattr(workflow, "retrieve_evidence", lambda context: ["data/docs/sample.md: evidence"])

    final_state = workflow.workflow_graph.invoke(create_initial_state("checkout timeout", ""))

    assert final_state["workflow_status"] == "completed"
    assert final_state["retrieved_docs"]
    assert final_state["log_findings"] == []
    assert final_state["root_causes"]


def test_supervisor_routes_empty_retrieval_to_fallback(monkeypatch) -> None:
    monkeypatch.setattr(workflow, "retrieve_evidence", lambda context: [])

    final_state = workflow.workflow_graph.invoke(
        create_initial_state("checkout timeout", "ERROR timeout from gateway")
    )

    assert final_state["workflow_status"] == "fallback_answer"
    assert final_state["root_causes"] == ["Insufficient evidence to infer a specific root cause."]
    assert "Fallback" in final_state["final_report"]


def test_supervisor_returns_clarification_when_information_is_insufficient() -> None:
    response = run_workflow(DiagnosisRequest(description="help"))

    assert response.root_causes == []
    assert "Clarification needed" in response.report
