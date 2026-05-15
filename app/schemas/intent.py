"""Intent extraction schemas."""

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
    """Structured output produced by the Intent Agent."""

    system: str | None = Field(default=None, description="Affected system or service.")
    symptom: str = Field(default="", description="Observed failure symptom.")
    error_codes: list[str] = Field(
        default_factory=list,
        description="Error codes mentioned by the user.",
    )
    time_range: str | None = Field(default=None, description="Time range of the incident.")
    severity: str = Field(default="unknown", description="Incident severity.")
