from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_diagnose_endpoint_runs_workflow() -> None:
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
    assert body["root_causes"]
    assert body["report"]
