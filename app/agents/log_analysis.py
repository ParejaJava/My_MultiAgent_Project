"""Minimal log analysis agent."""


def analyze_logs(logs: str) -> list[str]:
    """Return simple log pattern findings."""
    if not logs.strip():
        return []

    findings: list[str] = []
    lowered = logs.lower()
    if "error" in lowered:
        findings.append("Log contains error indicators.")
    if "timeout" in lowered:
        findings.append("Log contains timeout indicators.")
    return findings
