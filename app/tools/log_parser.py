"""Deterministic log parsing helpers."""


def has_error(logs: str) -> bool:
    """Return whether logs contain an error indicator."""
    return "error" in logs.lower()
