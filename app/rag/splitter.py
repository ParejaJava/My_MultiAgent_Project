"""Text splitting helpers for retrieval chunks."""


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
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
