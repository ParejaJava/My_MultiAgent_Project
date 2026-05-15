"""Markdown document loading helpers."""

from pathlib import Path


def load_markdown_documents(docs_dir: Path) -> list[tuple[Path, str]]:
    """Load markdown files from a directory."""
    if not docs_dir.exists():
        return []

    documents: list[tuple[Path, str]] = []
    for path in sorted(docs_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            documents.append((path, text))
    return documents
