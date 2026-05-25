"""Text splitting helpers for retrieval chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    """A text chunk plus metadata derived during splitting."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def split_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    strategy: str = "character",
) -> list[str]:
    """Split text into chunks while preserving the historical string output."""
    return [
        chunk.content
        for chunk in split_text_with_metadata(
            text,
            chunk_size=chunk_size,
            overlap=overlap,
            strategy=strategy,
        )
    ]


def split_text_with_metadata(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    strategy: str = "character",
) -> list[TextChunk]:
    """Split text and return optional chunk metadata."""
    normalized_strategy = strategy.lower()
    if normalized_strategy == "character":
        return [TextChunk(content=chunk) for chunk in split_character_text(text, chunk_size, overlap)]
    if normalized_strategy == "markdown":
        return split_markdown_text(text, chunk_size=chunk_size, overlap=overlap)
    raise ValueError("chunking strategy must be one of: character, markdown")


def split_character_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    stripped = text.strip()
    if not stripped:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(stripped):
        end = min(start + chunk_size, len(stripped))
        chunks.append(stripped[start:end].strip())
        if end == len(stripped):
            break
        start = end - overlap
    return [chunk for chunk in chunks if chunk]


def split_markdown_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[TextChunk]:
    """Split Markdown around structural boundaries before falling back to character chunks."""
    _validate_chunk_args(chunk_size, overlap)
    sections = parse_markdown_sections(text)
    chunks: list[TextChunk] = []
    for heading_path, body in sections:
        content = body.strip()
        if not content:
            continue
        if len(content) <= chunk_size:
            chunks.append(TextChunk(content=content, metadata=_heading_metadata(heading_path)))
            continue
        chunks.extend(split_large_markdown_section(content, heading_path, chunk_size, overlap))
    return chunks


def parse_markdown_sections(text: str) -> list[tuple[list[str], str]]:
    """Return Markdown sections with their heading paths."""
    stripped = text.strip()
    if not stripped:
        return []

    sections: list[tuple[list[str], list[str]]] = []
    current_heading_path: list[str] = []
    current_lines: list[str] = []
    heading_stack: list[tuple[int, str]] = []

    for line in stripped.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            if current_lines:
                sections.append((current_heading_path, current_lines))
            level = len(heading.group(1))
            title = heading.group(2).strip()
            heading_stack = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
            heading_stack.append((level, title))
            current_heading_path = [item_title for _, item_title in heading_stack]
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading_path, current_lines))

    return [
        (heading_path, "\n".join(lines).strip())
        for heading_path, lines in sections
        if "\n".join(lines).strip()
    ]


def split_large_markdown_section(
    text: str,
    heading_path: list[str],
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    """Split an oversized Markdown section by paragraphs and code blocks."""
    blocks = split_markdown_blocks(text)
    chunks: list[TextChunk] = []
    current = ""
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.extend(_chunk_markdown_part(current, heading_path, chunk_size, overlap))
        current = block
    if current:
        chunks.extend(_chunk_markdown_part(current, heading_path, chunk_size, overlap))
    return chunks


def split_markdown_blocks(text: str) -> list[str]:
    """Split Markdown into paragraph-like blocks while keeping fenced code intact."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _chunk_markdown_part(
    text: str,
    heading_path: list[str],
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    return [
        TextChunk(content=chunk, metadata=_heading_metadata(heading_path))
        for chunk in split_character_text(text, chunk_size=chunk_size, overlap=overlap)
    ]


def _heading_metadata(heading_path: list[str]) -> dict[str, Any]:
    if not heading_path:
        return {}
    return {"heading_path": " > ".join(heading_path)}


def _validate_chunk_args(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
