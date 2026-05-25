"""In-memory conversation session helpers."""

from __future__ import annotations

from uuid import uuid4


MAX_HISTORY_ITEMS = 12
_SESSIONS: dict[str, list[dict[str, str]]] = {}


def ensure_session_id(session_id: str | None = None) -> str:
    """Return a caller-provided session id or create a new one."""
    return session_id.strip() if session_id and session_id.strip() else uuid4().hex


def load_session_history(session_id: str) -> list[dict[str, str]]:
    """Return a copy of recent conversation history for a session."""
    return list(_SESSIONS.get(session_id, []))


def append_session_turn(session_id: str, user_message: str, assistant_message: str) -> None:
    """Append a user/assistant turn to the in-memory session history."""
    history = _SESSIONS.setdefault(session_id, [])
    history.extend(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]
    )
    _SESSIONS[session_id] = trim_history(history)


def trim_history(history: list[dict[str, str]], max_items: int = MAX_HISTORY_ITEMS) -> list[dict[str, str]]:
    """Keep only the most recent history items."""
    return history[-max_items:]


def clear_sessions() -> None:
    """Clear all in-memory sessions for tests."""
    _SESSIONS.clear()
