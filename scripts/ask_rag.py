"""Ask the RAG system a question and generate a diagnosis answer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import resolve_project_path  # noqa: E402
from app.rag.answer_generator import generate_answer  # noqa: E402
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, load_rag_config  # noqa: E402
from app.rag.hybrid_retriever import retrieve_hybrid_documents  # noqa: E402
from app.rag.retriever import retrieve_documents  # noqa: E402
from app.rag.vector_store import RetrievedDocument  # noqa: E402


def main() -> int:
    """Run command-line RAG QA."""
    parser = argparse.ArgumentParser(description="Ask RAG and generate a diagnostic answer.")
    parser.add_argument("--config", default=str(DEFAULT_RAG_CONFIG_PATH), help="Path to RAG config YAML.")
    parser.add_argument("--question", required=True, help="User question.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved documents.")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")

    config_path = resolve_project_path(args.config)
    config = load_rag_config(config_path)
    retrieved_documents = run_configured_retriever(args.question, args.top_k, config, config_path)
    result = generate_answer(args.question, retrieved_documents, config)

    print("Answer:")
    print(result.answer)
    print()
    print("Cited sources:")
    if result.cited_sources:
        for source in result.cited_sources:
            print(f"- {source}")
    else:
        print("- (none)")
    return 0


def run_configured_retriever(
    question: str,
    top_k: int,
    config: dict[str, Any],
    config_path: Path,
) -> list[RetrievedDocument]:
    """Run dense or hybrid retrieval based on config."""
    retriever = str(config.get("retriever", "dense")).lower()
    if retriever in {"dense", "chroma_dense"}:
        return retrieve_documents(question, top_k=top_k, config_path=config_path)
    if retriever == "hybrid_rrf":
        return retrieve_hybrid_documents(question, top_k=top_k, config_path=config_path)
    raise ValueError(f"Unsupported retriever '{retriever}'. Expected dense or hybrid_rrf.")


if __name__ == "__main__":
    raise SystemExit(main())
