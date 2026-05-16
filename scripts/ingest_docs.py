"""Ingest markdown documents into the local Chroma vector store."""

import argparse
from pathlib import Path

from app.config import settings
from app.rag.config import DEFAULT_RAG_CONFIG_PATH, get_collection_name, load_rag_config
from app.rag.embeddings import create_embedding_function
from app.rag.vector_store import ingest_documents


def main() -> int:
    """Run document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest markdown docs into Chroma.")
    parser.add_argument("--config", default=str(DEFAULT_RAG_CONFIG_PATH), help="Path to RAG config YAML.")
    parser.add_argument("--docs-dir", default="data/docs", help="Directory containing markdown files.")
    parser.add_argument(
        "--persist-dir",
        default=settings.vector_store_path,
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

    config = load_rag_config(args.config)
    chunking = config.get("chunking", {}) if isinstance(config.get("chunking"), dict) else {}
    collection_name = args.collection or get_collection_name(config)
    chunk_size = args.chunk_size or int(chunking.get("chunk_size", 500))
    overlap = args.overlap if args.overlap is not None else int(chunking.get("overlap", 50))
    embedding_function = create_embedding_function(config)

    count = ingest_documents(
        docs_dir=Path(args.docs_dir),
        persist_directory=Path(args.persist_dir),
        collection_name=collection_name,
        chunk_size=chunk_size,
        overlap=overlap,
        reset_collection=not args.no_reset,
        embedding_function=embedding_function,
    )
    print(f"Ingested {count} chunks into collection '{collection_name}' using config '{args.config}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
