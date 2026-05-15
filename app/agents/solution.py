"""Minimal solution agent."""


def generate_report(root_causes: list[str], evidence: list[str], log_findings: list[str]) -> str:
    """Generate a concise troubleshooting report."""
    sections = [
        "Summary: minimal diagnosis workflow completed.",
        f"Root causes: {'; '.join(root_causes)}",
    ]
    if evidence:
        sections.append(f"Evidence: {'; '.join(evidence)}")
    if log_findings:
        sections.append(f"Log findings: {'; '.join(log_findings)}")
    if not evidence and not log_findings:
        sections.append("Fallback: no external evidence or log patterns were found.")
    return "\n".join(sections)
