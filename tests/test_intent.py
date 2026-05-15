from app.agents.intent import extract_fault_context
from app.schemas.diagnosis import DiagnosisRequest


def test_extract_fault_context() -> None:
    request = DiagnosisRequest(
        service="payments",
        description="timeouts increased",
        logs="timeout while calling gateway",
    )

    context = extract_fault_context(request)

    assert context.service == "payments"
    assert context.description == "timeouts increased"
    assert "timeout" in context.logs
