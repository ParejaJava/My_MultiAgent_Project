"""Diagnosis request and response schemas."""

from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    """Incoming diagnosis request."""

    description: str = Field(..., min_length=1)
    service: str | None = None
    logs: str | None = None
    session_id: str | None = None


class FaultContext(BaseModel):
    """Structured fault context extracted from a request."""

    description: str
    service: str | None = None
    logs: str = ""


class EvidenceItem(BaseModel):
    """Structured evidence returned by retrieval or deterministic tools."""

    content: str
    source: str = "unknown"
    chunk_index: int | None = None
    score: float | None = None
    retrieval_method: str | None = None


class AgentStep(BaseModel):
    """Public execution trace summary for an agent step."""

    agent: str
    action: str
    status: str
    observation: str = ""
    sources: list[str] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    """Diagnosis workflow response."""

    session_id: str
    route: str
    needs_clarification: bool = False
    clarification_question: str | None = None
    service: str | None
    root_causes: list[str]
    evidence: list[str]
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    agent_steps: list[AgentStep] = Field(default_factory=list)
    log_findings: list[str]
    report: str
