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
