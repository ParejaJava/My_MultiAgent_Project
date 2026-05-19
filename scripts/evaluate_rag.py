"""Offline retrieval evaluation for the local RAG system."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import resolve_project_path  # noqa: E402
from app.rag.retriever import retrieve_documents  # noqa: E402
from app.rag.config import load_rag_config  # noqa: E402
from app.rag.hybrid_retriever import retrieve_hybrid_documents  # noqa: E402
from app.rag.reranker import get_reranker_metadata  # noqa: E402
from app.rag.storage_check import ensure_chroma_persistence_ready, ensure_directory_ready  # noqa: E402
from app.config import settings  # noqa: E402


REQUIRED_FIELDS = {
    "id",
    "question",
    "category",
    "difficulty",
    "expected_sources",
    "expected_keywords",
    "reference_answer",
}


def main() -> int:
    """Run offline retrieval evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality without LLM calls.")
    parser.add_argument("--config", default="configs/rag/baseline_hash.yaml", help="Path to RAG experiment config.")
    parser.add_argument("--eval-file", default="eval/questions.jsonl", help="Path to JSONL eval file.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved chunks to evaluate.")
    parser.add_argument("--output-dir", default="eval/results", help="Directory for evaluation outputs.")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")

    config_path = resolve_project_path(args.config)
    eval_file = resolve_project_path(args.eval_file)
    output_dir = resolve_project_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    validate_retrieval_storage(config)
    config_name = str(config.get("name") or config_path.stem)
    questions = load_questions(eval_file)
    samples = [evaluate_question(row, args.top_k, config_path=config_path) for row in questions]
    metrics = summarize(samples, args.top_k)
    retrieval_metadata = get_retrieval_metadata(config, args.top_k)
    report = {
        "config_name": config_name,
        "git_commit": get_git_commit(),
        "top_k": args.top_k,
        "eval_file": normalize_source(str(eval_file)),
        "timestamp": datetime.now(UTC).isoformat(),
        "config_path": normalize_source(str(config_path)),
        "config": config,
        "retriever": retrieval_metadata,
        "reranker": get_reranker_metadata(
            config,
            retrieve_top_n=int(retrieval_metadata["retrieve_top_n"]),
            rerank_top_k=int(retrieval_metadata["rerank_top_k"]),
        ),
        "metrics": metrics,
        "samples": samples,
    }

    json_path = output_dir / "rag_eval.json"
    markdown_path = output_dir / "rag_eval.md"
    write_json(json_path, report)
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")

    print(f"Config: {config_name}")
    print(f"Evaluated {metrics['total_questions']} questions")
    print(f"Recall@{args.top_k}: {metrics['recall_at_k']:.4f}")
    print(f"Precision@{args.top_k}: {metrics['precision_at_k']:.4f}")
    print(f"Hit Rate@{args.top_k}: {metrics['hit_rate_at_k']:.4f}")
    print(f"MRR: {metrics['mrr']:.4f}")
    print(f"NDCG@{args.top_k}: {metrics['ndcg_at_k']:.4f}")
    print(f"Wrote {json_path} and {markdown_path}")
    return 0


def load_config(path: Path) -> dict[str, Any]:
    """Load an experiment config from YAML."""
    return load_rag_config(path)


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the simple YAML subset used by local RAG configs."""
    root: dict[str, Any] = {}
    current_map_key: str | None = None
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key, value = split_yaml_key_value(raw_line)
            current_map_key = None
            current_list_key = None
            if value == "":
                root[key] = {}
                current_map_key = key
            else:
                root[key] = parse_yaml_scalar(value)
        elif raw_line.startswith("  - ") and current_list_key:
            root[current_list_key].append(parse_yaml_scalar(raw_line.strip()[2:].strip()))
        elif raw_line.startswith("  - "):
            if current_map_key is None:
                continue
            root[current_map_key] = [parse_yaml_scalar(raw_line.strip()[2:].strip())]
            current_list_key = current_map_key
            current_map_key = None
        elif raw_line.startswith("  ") and current_map_key:
            key, value = split_yaml_key_value(raw_line.strip())
            child = root[current_map_key]
            if isinstance(child, dict):
                child[key] = parse_yaml_scalar(value)
    return root


def split_yaml_key_value(line: str) -> tuple[str, str]:
    """Split a YAML key-value line."""
    key, _, value = line.partition(":")
    return key.strip(), value.strip()


def parse_yaml_scalar(value: str) -> Any:
    """Parse a small subset of YAML scalar values."""
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


def get_git_commit() -> str | None:
    """Return the current git commit hash when available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    commit = result.stdout.strip()
    return commit or None


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load and validate JSONL evaluation questions."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        validate_question(row, line_number)
        rows.append(row)
    return rows


def validate_question(row: dict[str, Any], line_number: int) -> None:
    """Validate one evaluation question row."""
    missing = REQUIRED_FIELDS.difference(row)
    if missing:
        raise ValueError(f"Line {line_number} missing required fields: {sorted(missing)}")
    if row["difficulty"] not in {"easy", "medium", "hard"}:
        raise ValueError(f"Line {line_number} has invalid difficulty: {row['difficulty']}")
    if not isinstance(row["expected_sources"], list) or not row["expected_sources"]:
        raise ValueError(f"Line {line_number} expected_sources must be a non-empty list")


def evaluate_question(row: dict[str, Any], top_k: int, config_path: Path | str | None = None) -> dict[str, Any]:
    """Evaluate retrieval for one question."""
    config = load_rag_config(config_path or "configs/rag/baseline_hash.yaml")
    retrieved_docs = run_retriever(row["question"], top_k=top_k, config=config, config_path=config_path)
    retrieved_sources = [
        normalize_source(document.metadata.get("source", ""))
        for document in retrieved_docs[:top_k]
    ]
    relevant_sources = {normalize_source(source) for source in row["expected_sources"]}
    relevance = rank_relevance(retrieved_sources, relevant_sources)
    hit_count = len(set(retrieved_sources).intersection(relevant_sources))

    return {
        "id": row["id"],
        "question": row["question"],
        "category": row["category"],
        "difficulty": row["difficulty"],
        "expected_sources": sorted(relevant_sources),
        "expected_keywords": row["expected_keywords"],
        "reference_answer": row["reference_answer"],
        "retrieved_sources": retrieved_sources,
        "retrieved": [
            {
                "rank": index + 1,
                "source": retrieved_sources[index],
                "score": retrieved_docs[index].score,
                "chunk_index": retrieved_docs[index].metadata.get("chunk_index"),
                "metadata": retrieved_docs[index].metadata,
                "content_preview": retrieved_docs[index].content[:240],
            }
            for index in range(len(retrieved_sources))
        ],
        "hit_count": hit_count,
        "missed_sources": sorted(relevant_sources.difference(retrieved_sources)),
        "recall_at_k": recall_at_k(retrieved_sources, relevant_sources),
        "precision_at_k": precision_at_k(retrieved_sources, relevant_sources, top_k),
        "hit_rate_at_k": 1.0 if hit_count > 0 else 0.0,
        "rr": reciprocal_rank(relevance),
        "ndcg_at_k": ndcg_at_k(relevance, min(len(relevant_sources), top_k)),
    }


def run_retriever(
    question: str,
    top_k: int,
    config: dict[str, Any],
    config_path: Path | str | None = None,
) -> list[Any]:
    """Run the configured retriever."""
    retriever = str(config.get("retriever", "dense")).lower()
    if retriever in {"dense", "chroma_dense"}:
        return retrieve_documents(question, top_k=top_k, config_path=config_path)
    if retriever == "hybrid_rrf":
        return retrieve_hybrid_documents(question, top_k=top_k, config_path=config_path)
    raise ValueError(f"Unsupported retriever '{retriever}'. Expected dense or hybrid_rrf.")


def validate_retrieval_storage(config: dict[str, Any]) -> None:
    """Fail fast when configured local retrieval storage cannot support persistence."""
    retriever = str(config.get("retriever", "dense")).lower()
    persist_directory = config.get("persist_directory") or settings.vector_store_path
    if retriever in {"dense", "chroma_dense", "hybrid_rrf"}:
        ensure_chroma_persistence_ready(persist_directory)
    if retriever == "hybrid_rrf":
        bm25_config = config.get("bm25", {}) if isinstance(config.get("bm25"), dict) else {}
        ensure_directory_ready(bm25_config.get("index_directory", settings.bm25_index_path), label="BM25 index directory")


def get_retrieval_metadata(config: dict[str, Any], top_k: int) -> dict[str, Any]:
    """Return retriever metadata for evaluation reports."""
    ranking = config.get("ranking", {}) if isinstance(config.get("ranking"), dict) else {}
    retriever = str(config.get("retriever", "dense")).lower()
    retrieve_top_n = int(ranking.get("retrieve_top_n", ranking.get("top_n", max(top_k * 2, top_k))))
    rerank_top_k = int(ranking.get("rerank_top_k", top_k))
    return {
        "provider": retriever,
        "retrieve_top_n": retrieve_top_n,
        "rerank_top_k": rerank_top_k,
    }


def recall_at_k(retrieved_sources: list[str], relevant_sources: set[str]) -> float:
    """Compute source-level Recall@K."""
    if not relevant_sources:
        return 0.0
    return len(set(retrieved_sources).intersection(relevant_sources)) / len(relevant_sources)


def precision_at_k(retrieved_sources: list[str], relevant_sources: set[str], top_k: int) -> float:
    """Compute source-level Precision@K using K as denominator."""
    if top_k <= 0:
        return 0.0
    return len(set(retrieved_sources).intersection(relevant_sources)) / top_k


def rank_relevance(retrieved_sources: list[str], relevant_sources: set[str]) -> list[int]:
    """Return binary relevance by rank, counting each relevant source once."""
    seen_relevant: set[str] = set()
    relevance: list[int] = []
    for source in retrieved_sources:
        if source in relevant_sources and source not in seen_relevant:
            relevance.append(1)
            seen_relevant.add(source)
        else:
            relevance.append(0)
    return relevance


def reciprocal_rank(relevance: list[int]) -> float:
    """Return reciprocal rank for the first relevant result."""
    for index, is_relevant in enumerate(relevance, start=1):
        if is_relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(relevance: list[int], ideal_relevant_count: int) -> float:
    """Compute binary NDCG@K."""
    dcg = sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevance, start=1))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_relevant_count + 1))
    return 0.0 if idcg == 0 else dcg / idcg


def summarize(samples: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    """Aggregate per-question metrics."""
    total = len(samples)
    if total == 0:
        return {
            "total_questions": 0,
            "top_k": top_k,
            "recall_at_k": 0.0,
            "precision_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
            "failed_count": 0,
        }

    return {
        "total_questions": total,
        "top_k": top_k,
        "recall_at_k": average(samples, "recall_at_k"),
        "precision_at_k": average(samples, "precision_at_k"),
        "hit_rate_at_k": average(samples, "hit_rate_at_k"),
        "mrr": average(samples, "rr"),
        "ndcg_at_k": average(samples, "ndcg_at_k"),
        "failed_count": sum(1 for sample in samples if sample["hit_count"] == 0),
        "by_category": summarize_by(samples, "category"),
        "by_difficulty": summarize_by(samples, "difficulty"),
    }


def summarize_by(samples: list[dict[str, Any]], field: str) -> dict[str, dict[str, float]]:
    """Aggregate metrics grouped by a sample field."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        groups.setdefault(sample[field], []).append(sample)
    return {
        group: {
            "count": len(rows),
            "recall_at_k": average(rows, "recall_at_k"),
            "precision_at_k": average(rows, "precision_at_k"),
            "hit_rate_at_k": average(rows, "hit_rate_at_k"),
            "mrr": average(rows, "rr"),
            "ndcg_at_k": average(rows, "ndcg_at_k"),
        }
        for group, rows in sorted(groups.items())
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a Markdown evaluation report."""
    summary = report["metrics"]
    samples = report["samples"]
    top_k = summary["top_k"]
    lines = [
        "# RAG Retrieval Evaluation",
        "",
        "## Run Metadata",
        "",
        f"- Config: `{report['config_name']}`",
        f"- Git commit: `{report['git_commit'] or 'unknown'}`",
        f"- Eval file: `{report['eval_file']}`",
        f"- Top K: `{report['top_k']}`",
        f"- Retriever: `{report['retriever']['provider']}`",
        f"- Retrieve top N: `{report['retriever']['retrieve_top_n']}`",
        f"- Rerank top K: `{report['retriever']['rerank_top_k']}`",
        f"- Reranker: `{report['reranker']['provider']}`",
        f"- Reranker model: `{report['reranker']['model'] or 'none'}`",
        f"- Timestamp: `{report['timestamp']}`",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total Questions | {summary['total_questions']} |",
        f"| Recall@{top_k} | {summary['recall_at_k']:.4f} |",
        f"| Precision@{top_k} | {summary['precision_at_k']:.4f} |",
        f"| Hit Rate@{top_k} | {summary['hit_rate_at_k']:.4f} |",
        f"| MRR | {summary['mrr']:.4f} |",
        f"| NDCG@{top_k} | {summary['ndcg_at_k']:.4f} |",
        f"| Failed Samples | {summary['failed_count']} |",
        "",
        "## Metrics By Category",
        "",
        "| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, metrics in summary.get("by_category", {}).items():
        lines.append(render_group_row(category, metrics))

    lines.extend(
        [
            "",
            "## Failed Samples",
            "",
        ]
    )
    failed = [sample for sample in samples if sample["hit_count"] == 0]
    if not failed:
        lines.append("No failed samples.")
    else:
        for sample in failed:
            lines.extend(
                [
                    f"### {sample['id']}",
                    f"- Category: {sample['category']}",
                    f"- Difficulty: {sample['difficulty']}",
                    f"- Question: {sample['question']}",
                    f"- Expected sources: {', '.join(sample['expected_sources'])}",
                    f"- Retrieved sources: {', '.join(sample['retrieved_sources']) or '(none)'}",
                    f"- Expected keywords: {', '.join(sample['expected_keywords'])}",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def render_group_row(name: str, metrics: dict[str, float]) -> str:
    """Render one grouped metrics row."""
    return (
        f"| {name} | {int(metrics['count'])} | {metrics['recall_at_k']:.4f} | "
        f"{metrics['precision_at_k']:.4f} | {metrics['hit_rate_at_k']:.4f} | "
        f"{metrics['mrr']:.4f} | {metrics['ndcg_at_k']:.4f} |"
    )


def average(rows: list[dict[str, Any]], metric: str) -> float:
    """Average a numeric metric."""
    return sum(float(row[metric]) for row in rows) / len(rows)


def normalize_source(source: str) -> str:
    """Normalize source paths for matching."""
    return source.replace("\\", "/")


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON output."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
