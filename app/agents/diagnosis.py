"""Minimal diagnosis agent."""

from app.schemas.diagnosis import FaultContext


def infer_root_causes(context: FaultContext, evidence: list[str]) -> list[str]:
    """Infer placeholder root causes from structured context and evidence."""
    if evidence:
        return ["Possible issue related to retrieved operational evidence."]
    if context.service:
        return [f"Possible issue affecting service '{context.service}'."]
    return ["Insufficient evidence to infer a specific root cause."]
