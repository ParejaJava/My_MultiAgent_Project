"""Intent extraction agent."""

import re

from app.schemas.diagnosis import DiagnosisRequest, FaultContext
from app.schemas.intent import IntentOutput


ERROR_CODE_PATTERN = re.compile(r"\b(?:HTTP\s*)?[45]\d{2}\b|\b[A-Z][A-Z0-9_]{2,}\d*\b")
TIME_RANGE_PATTERN = re.compile(
    r"\b(?:last|past)\s+\d+\s+(?:minutes?|mins?|hours?|hrs?|days?)\b"
    r"|\b\d+\s*(?:minutes?|mins?|hours?|hrs?|days?)\s+ago\b"
    r"|\b(?:today|yesterday|tonight|this morning|this afternoon)\b",
    re.IGNORECASE,
)
SYSTEM_PATTERNS = (
    re.compile(r"\b([a-zA-Z0-9_-]+)\s+(?:service|system|app|application)\b", re.IGNORECASE),
    re.compile(r"\b(?:service|system|app|application)\s+['\"]?([a-zA-Z0-9_-]+)['\"]?", re.IGNORECASE),
)
SYSTEM_STOPWORDS = {"has", "is", "was", "were", "with", "shows", "returns", "reports"}
SEVERITY_KEYWORDS = {
    "critical": ("critical", "sev1", "p0", "outage", "down", "unavailable"),
    "high": ("high", "sev2", "p1", "major", "failing", "failed"),
    "medium": ("medium", "sev3", "p2", "degraded", "slow", "latency", "timeout"),
    "low": ("low", "sev4", "p3", "minor", "warning"),
}


def extract_intent(user_question: str) -> IntentOutput:
    """Extract structured incident intent from a user question using rules."""
    text = user_question.strip()
    return IntentOutput(
        system=_extract_system(text),
        symptom=_extract_symptom(text),
        error_codes=_extract_error_codes(text),
        time_range=_extract_time_range(text),
        severity=_extract_severity(text),
    )


def extract_fault_context(request: DiagnosisRequest) -> FaultContext:
    """Extract basic fault information from the incoming request."""
    intent = extract_intent(request.description)
    return FaultContext(
        service=request.service or intent.system,
        description=intent.symptom or request.description,
        logs=request.logs or "",
    )


def _extract_system(text: str) -> str | None:
    for pattern in SYSTEM_PATTERNS:
        match = pattern.search(text)
        if match and match.group(1).lower() not in SYSTEM_STOPWORDS:
            return match.group(1)
    return None


def _extract_symptom(text: str) -> str:
    if not text:
        return ""

    cleaned = ERROR_CODE_PATTERN.sub("", text)
    cleaned = TIME_RANGE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned or text


def _extract_error_codes(text: str) -> list[str]:
    codes = [match.group(0).replace("HTTP ", "") for match in ERROR_CODE_PATTERN.finditer(text)]
    return list(dict.fromkeys(codes))


def _extract_time_range(text: str) -> str | None:
    match = TIME_RANGE_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_severity(text: str) -> str:
    lowered = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return severity
    return "unknown"
