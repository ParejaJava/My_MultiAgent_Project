"""Minimal local document retriever."""

from pathlib import Path


DOCS_DIR = Path("data/docs")


def retrieve_documents(query: str, limit: int = 3) -> list[str]:
    """Retrieve simple text snippets from local documents."""
    if not query.strip() or not DOCS_DIR.exists():
        return []

    query_terms = {term.lower() for term in query.split() if term.strip()}
    matches: list[str] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if any(term in text.lower() for term in query_terms):
            matches.append(f"{path.as_posix()}: {text.strip()[:200]}")
        if len(matches) >= limit:
            break
    return matches
