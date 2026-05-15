"""Minimal intent extraction agent."""

from app.schemas.diagnosis import DiagnosisRequest, FaultContext


def extract_fault_context(request: DiagnosisRequest) -> FaultContext:
    """Extract basic fault information from the incoming request."""
    return FaultContext(
        service=request.service,
        description=request.description,
        logs=request.logs or "",
    )
