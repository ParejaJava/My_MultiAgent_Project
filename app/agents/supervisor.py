"""Minimal supervisor agent."""


def route_next_step(step: str) -> str:
    """Return the next workflow step name."""
    routes = {
        "intent": "retrieval",
        "retrieval": "log_analysis",
        "log_analysis": "diagnosis",
        "diagnosis": "solution",
    }
    return routes.get(step, "done")
