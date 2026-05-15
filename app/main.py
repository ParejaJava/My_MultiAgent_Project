"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings
from app.graph.workflow import run_workflow
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.schemas.health import HealthResponse


app = FastAPI(title=settings.app_name)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health."""
    return HealthResponse(status="ok", environment=settings.app_env)


@app.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """Run the minimal diagnosis workflow."""
    return run_workflow(request)
