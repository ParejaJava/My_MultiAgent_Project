from fastapi.testclient import TestClient

import app.main as main
from app.main import app
from app.schemas.diagnosis import DiagnosisResponse


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_diagnose_endpoint_runs_workflow(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_workflow",
        lambda request: DiagnosisResponse(
            session_id=request.session_id or "test-session",
            route="operations",
            needs_clarification=False,
            clarification_question=None,
            service=request.service,
            root_causes=["Downstream timeout"],
            evidence=["data/docs/sample.md: timeout evidence"],
            evidence_items=[],
            agent_steps=[
                {
                    "agent": "operations",
                    "action": "plan",
                    "status": "completed",
                    "observation": "Planned steps.",
                    "sources": [],
                }
            ],
            log_findings=["Detected timeout log pattern."],
            report="Diagnosis report",
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/diagnose",
        json={
            "service": "checkout",
            "description": "timeout errors",
            "logs": "ERROR timeout from gateway",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "checkout"
    assert body["session_id"] == "test-session"
    assert body["route"] == "operations"
    assert body["root_causes"]
    assert body["agent_steps"]
    assert body["report"]
