"""Compare multiple offline RAG evaluation runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import resolve_project_path  # noqa: E402


def main() -> int:
    """Render a Markdown comparison table for RAG eval JSON files."""
    parser = argparse.ArgumentParser(description="Compare RAG evaluation JSON runs.")
    parser.add_argument("runs", nargs="+", help="Evaluation JSON files to compare.")
    parser.add_argument("--output-file", help="Optional Markdown output file.")
    args = parser.parse_args()

    rows = [load_run(resolve_project_path(path)) for path in args.runs]
    markdown = render_comparison(rows)
    if args.output_file:
        resolve_project_path(args.output_file).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


def load_run(path: Path) -> dict[str, Any]:
    """Load one evaluation JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or data.get("summary") or {}
    return {
        "file": normalize_source(str(path)),
        "config_name": data.get("config_name") or "unknown",
        "git_commit": data.get("git_commit"),
        "top_k": data.get("top_k") or metrics.get("top_k"),
        "eval_file": data.get("eval_file") or "unknown",
        "timestamp": data.get("timestamp") or "unknown",
        "metrics": metrics,
    }


def render_comparison(rows: list[dict[str, Any]]) -> str:
    """Render comparison rows as a Markdown table."""
    lines = [
        "# RAG Run Comparison",
        "",
        "| Run | Config | Top K | Eval File | Timestamp | Recall@k | Precision@k | Hit Rate@k | MRR | NDCG@k | Git Commit |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        metrics = row["metrics"]
        lines.append(
            "| {file} | {config_name} | {top_k} | {eval_file} | {timestamp} | "
            "{recall:.4f} | {precision:.4f} | {hit_rate:.4f} | {mrr:.4f} | {ndcg:.4f} | {commit} |".format(
                file=row["file"],
                config_name=row["config_name"],
                top_k=row["top_k"],
                eval_file=row["eval_file"],
                timestamp=row["timestamp"],
                recall=float(metrics.get("recall_at_k", 0.0)),
                precision=float(metrics.get("precision_at_k", 0.0)),
                hit_rate=float(metrics.get("hit_rate_at_k", 0.0)),
                mrr=float(metrics.get("mrr", 0.0)),
                ndcg=float(metrics.get("ndcg_at_k", 0.0)),
                commit=(row["git_commit"] or "unknown")[:12],
            )
        )
    return "\n".join(lines) + "\n"


def normalize_source(source: str) -> str:
    """Normalize source paths for display."""
    return source.replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
