"""Ingest markdown documents into the local Chroma vector store."""

import argparse
from pathlib import Path

from app.config import settings
from app.rag.vector_store import DEFAULT_COLLECTION_NAME, ingest_documents


def main() -> int:
    """Run document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest markdown docs into Chroma.")
    parser.add_argument("--docs-dir", default="data/docs", help="Directory containing markdown files.")
    parser.add_argument(
        "--persist-dir",
        default=settings.vector_store_path,
        help="Chroma persistence directory.",
    )
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME, help="Chroma collection name.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size in characters.")
    parser.add_argument("--overlap", type=int, default=50, help="Chunk overlap in characters.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Append to the existing collection instead of recreating it.",
    )
    args = parser.parse_args()

    count = ingest_documents(
        docs_dir=Path(args.docs_dir),
        persist_directory=Path(args.persist_dir),
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        reset_collection=not args.no_reset,
    )
    print(f"Ingested {count} chunks into collection '{args.collection}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
