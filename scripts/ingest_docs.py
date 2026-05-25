"""Ingest markdown documents into the local Chroma vector store."""

import argparse
from pathlib import Path

from app.config import resolve_project_path, settings
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, get_collection_name, load_rag_config
from app.rag.embeddings import create_embedding_function
from app.rag.storage_check import ensure_chroma_persistence_ready
from app.rag.vector_store import ingest_documents


def main() -> int:
    """Run document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest markdown docs into Chroma.")
    parser.add_argument("--config", default=str(DEFAULT_RAG_CONFIG_PATH), help="Path to RAG config YAML.")
    parser.add_argument("--docs-dir", help="Override directory containing markdown files.")
    parser.add_argument(
        "--persist-dir",
        default=None,
        help="Chroma persistence directory.",
    )
    parser.add_argument("--collection", help="Override Chroma collection name from config.")
    parser.add_argument("--chunk-size", type=int, help="Override chunk size in characters.")
    parser.add_argument("--overlap", type=int, help="Override chunk overlap in characters.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Append to the existing collection instead of recreating it.",
    )
    args = parser.parse_args()

    config_path = resolve_project_path(args.config)
    config = load_rag_config(config_path)
    chunking = config.get("chunking", {}) if isinstance(config.get("chunking"), dict) else {}
    configured_docs_dirs = config.get("docs_dirs")
    configured_docs_dir = config.get("docs_dir", "data/docs")
    docs_dirs = None
    docs_dir = args.docs_dir or configured_docs_dir
    if args.docs_dir is None and isinstance(configured_docs_dirs, list):
        docs_dirs = [str(path) for path in configured_docs_dirs]
    persist_directory = args.persist_dir or config.get("persist_directory") or settings.vector_store_path
    persist_directory = ensure_chroma_persistence_ready(persist_directory)
    collection_name = args.collection or get_collection_name(config)
    chunk_size = args.chunk_size or int(chunking.get("chunk_size", 500))
    overlap = args.overlap if args.overlap is not None else int(chunking.get("overlap", 50))
    chunking_strategy = str(chunking.get("strategy", "character"))
    embedding_function = create_embedding_function(config)

    count = ingest_documents(
        docs_dir=Path(docs_dir),
        docs_dirs=[Path(path) for path in docs_dirs] if docs_dirs else None,
        persist_directory=persist_directory,
        collection_name=collection_name,
        chunk_size=chunk_size,
        overlap=overlap,
        chunking_strategy=chunking_strategy,
        reset_collection=not args.no_reset,
        embedding_function=embedding_function,
        allow_memory_fallback=False,
    )
    print(f"Ingested {count} chunks into collection '{collection_name}' using config '{config_path}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
