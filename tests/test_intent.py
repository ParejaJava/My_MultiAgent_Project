from app.agents.intent import extract_fault_context, extract_intent
from app.schemas.diagnosis import DiagnosisRequest


def test_extract_intent_from_user_question() -> None:
    intent = extract_intent(
        "checkout service has HTTP 503 timeout errors during the last 2 hours, sev2"
    )

    assert intent.system == "checkout"
    assert "503" in intent.error_codes
    assert intent.time_range == "last 2 hours"
    assert intent.severity == "high"
    assert "timeout errors" in intent.symptom


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


def test_extract_fault_context_uses_intent_system_when_service_missing() -> None:
    request = DiagnosisRequest(description="billing service is degraded today")

    context = extract_fault_context(request)

    assert context.service == "billing"
