"""RAG configuration loading helpers."""

from pathlib import Path
from typing import Any


DEFAULT_RAG_CONFIG_PATH = Path("configs/rag/baseline_hash.yaml")


def load_rag_config(path: Path | str = DEFAULT_RAG_CONFIG_PATH) -> dict[str, Any]:
    """Load a RAG config file from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"RAG config file not found: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(text)


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by local RAG configs."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_yaml_scalar(line[2:].strip()))
            continue

        key, value = split_yaml_key_value(line)
        if value == "":
            next_container: dict[str, Any] | list[Any]
            next_container = [] if next_non_empty_line_is_list(text, raw_line) else {}
            if isinstance(parent, dict):
                parent[key] = next_container
                stack.append((indent, next_container))
        elif isinstance(parent, dict):
            parent[key] = parse_yaml_scalar(value)

    return root


def next_non_empty_line_is_list(text: str, current_line: str) -> bool:
    """Return whether the next meaningful line after current_line is a YAML list item."""
    lines = text.splitlines()
    try:
        start = lines.index(current_line) + 1
    except ValueError:
        return False
    current_indent = len(current_line) - len(current_line.lstrip(" "))
    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        return indent > current_indent and line.strip().startswith("- ")
    return False


def split_yaml_key_value(line: str) -> tuple[str, str]:
    """Split a YAML key-value line."""
    key, _, value = line.partition(":")
    return key.strip(), value.strip()


def parse_yaml_scalar(value: str) -> Any:
    """Parse a scalar value from the local YAML subset."""
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value.strip("\"'")


def get_collection_name(config: dict[str, Any]) -> str:
    """Return the Chroma collection name for a RAG config."""
    collection_name = config.get("collection_name")
    if not collection_name:
        raise ValueError("RAG config must define collection_name to avoid embedding space mixing")
    return str(collection_name)


def get_embedding_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the embedding section from a RAG config."""
    embedding = config.get("embedding")
    if not isinstance(embedding, dict):
        raise ValueError("RAG config must define an embedding mapping")
    return embedding
