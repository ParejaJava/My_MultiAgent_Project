"""Storage health checks for local retrieval indexes."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.config import resolve_project_path


def ensure_directory_ready(path: Path | str, label: str = "storage directory") -> Path:
    """Ensure a directory supports write, atomic replace, and delete operations."""
    directory = resolve_project_path(path)
    probe_id = uuid4().hex
    probe_path = directory / f".{probe_id}.probe"
    replaced_path = directory / f".{probe_id}.replaced"

    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("probe", encoding="ascii")
        os.replace(probe_path, replaced_path)
        if replaced_path.read_text(encoding="ascii") != "probe":
            raise OSError("probe content mismatch after atomic replace")
        replaced_path.unlink()
    except Exception as exc:
        _cleanup_paths(probe_path, replaced_path)
        raise RuntimeError(
            f"{label} is not safe for local index persistence: {directory}. "
            "The directory must allow file create, write, atomic replace, and delete."
        ) from exc

    return directory


def ensure_chroma_persistence_ready(path: Path | str) -> Path:
    """Ensure a Chroma directory can support SQLite transactions."""
    directory = ensure_directory_ready(path, label="Chroma persistence directory")
    probe_id = uuid4().hex
    db_path = directory / f".{probe_id}.sqlite3"
    journal_path = directory / f".{probe_id}.sqlite3-journal"
    wal_path = directory / f".{probe_id}.sqlite3-wal"
    shm_path = directory / f".{probe_id}.sqlite3-shm"

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("CREATE TABLE probe (value INTEGER NOT NULL)")
            connection.execute("INSERT INTO probe VALUES (1)")
            connection.commit()
        finally:
            connection.close()
        db_path.unlink()
        _cleanup_paths(journal_path, wal_path, shm_path)
    except Exception as exc:
        _cleanup_paths(db_path, journal_path, wal_path, shm_path)
        raise RuntimeError(
            f"Chroma persistence directory cannot complete a SQLite transaction: {directory}. "
            "Use a local, non-synced directory with full Windows user permissions."
        ) from exc

    return directory


def _cleanup_paths(*paths: Path) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue
