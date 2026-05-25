"""Markdown document loading helpers."""

from pathlib import Path
from typing import Iterable


def load_markdown_documents(docs_dir: Path) -> list[tuple[Path, str]]:
    """Load markdown files from one directory."""
    return load_markdown_documents_from_dirs([docs_dir])


def load_markdown_documents_from_dirs(docs_dirs: Iterable[Path]) -> list[tuple[Path, str]]:
    """Load markdown files from multiple directories in stable order."""
    documents: list[tuple[Path, str]] = []
    seen_paths: set[Path] = set()
    for docs_dir in docs_dirs:
        if not docs_dir.exists():
            continue
        for path in sorted(docs_dir.rglob("*.md")):
            resolved_path = path.resolve()
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            text = path.read_text(encoding="utf-8").strip()
            if text:
                documents.append((path, text))
    return documents
