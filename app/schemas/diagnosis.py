"""Diagnosis request and response schemas."""

from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    """Incoming diagnosis request."""

    description: str = Field(..., min_length=1)
    service: str | None = None
    logs: str | None = None


class FaultContext(BaseModel):
    """Structured fault context extracted from a request."""

    description: str
    service: str | None = None
    logs: str = ""


class DiagnosisResponse(BaseModel):
    """Diagnosis workflow response."""

    service: str | None
    root_causes: list[str]
    evidence: list[str]
    log_findings: list[str]
    report: str
