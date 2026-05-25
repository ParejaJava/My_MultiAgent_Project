"""Run the stress RAG optimization benchmark suite."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import resolve_project_path  # noqa: E402
from app.rag.answer_generator import generate_answer  # noqa: E402
from app.rag.config import load_rag_config  # noqa: E402
from scripts.ask_rag import run_configured_retriever  # noqa: E402
from scripts.evaluate_rag import (  # noqa: E402
    evaluate_question,
    get_git_commit,
    get_retrieval_metadata,
    load_questions,
    normalize_source,
    render_markdown_report,
    summarize,
    validate_retrieval_storage,
    write_json,
)
from app.rag.reranker import get_reranker_metadata  # noqa: E402


DEFAULT_SUITE_RUNS = [
    {
        "id": "dense_character",
        "label": "Dense BGE + character chunking",
        "config": "configs/rag/bge_local_stress_character.yaml",
    },
    {
        "id": "hybrid_character",
        "label": "Hybrid BGE + BM25 + character chunking",
        "config": "configs/rag/hybrid_bge_rrf_stress_character.yaml",
    },
    {
        "id": "hybrid_rerank_character",
        "label": "Hybrid BGE + BM25 + BGE reranker + character chunking",
        "config": "configs/rag/hybrid_rrf_rerank_stress_character.yaml",
    },
    {
        "id": "hybrid_rerank_markdown",
        "label": "Hybrid BGE + BM25 + BGE reranker + markdown-aware chunking",
        "config": "configs/rag/hybrid_rrf_rerank_stress_markdown.yaml",
    },
]


DEFAULT_LLM_QUESTION = "Redis READONLY 怎么处理？"
RETRIEVAL_SIGNIFICANT_THRESHOLD = 0.10
CHUNKING_SIGNIFICANT_THRESHOLD = 0.05


def main() -> int:
    """Run all configured stress benchmark runs and render the optimization report."""
    parser = argparse.ArgumentParser(description="Run RAG optimization benchmark suite.")
    parser.add_argument("--eval-file", default="eval/questions_stress.jsonl", help="Path to JSONL eval file.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved chunks to evaluate.")
    parser.add_argument("--output-dir", default="eval/results/rag_optimization", help="Suite output directory.")
    parser.add_argument("--report-file", default="eval/results/rag_optimization_report.md", help="Markdown report path.")
    parser.add_argument("--llm-question", default=DEFAULT_LLM_QUESTION, help="Representative question for LLM validation.")
    parser.add_argument("--skip-llm-validation", action="store_true", help="Skip the representative Kimi answer check.")
    parser.add_argument(
        "--require-llm-validation",
        action="store_true",
        help="Return a non-zero exit code if representative LLM validation fails.",
    )
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be greater than 0")

    output_dir = resolve_project_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = [
        run_suite_evaluation(
            run=run,
            eval_file=resolve_project_path(args.eval_file),
            top_k=args.top_k,
            output_dir=output_dir / run["id"],
        )
        for run in DEFAULT_SUITE_RUNS
    ]
    llm_validation = (
        {"status": "skipped", "question": args.llm_question, "answer_preview": "", "cited_sources": [], "error": ""}
        if args.skip_llm_validation
        else run_llm_validation(args.llm_question, DEFAULT_SUITE_RUNS[-1]["config"], args.top_k)
    )
    markdown = render_optimization_report(reports, llm_validation)
    resolve_project_path(args.report_file).write_text(markdown, encoding="utf-8")

    print(f"Wrote {args.report_file}")
    for report in reports:
        metrics = report["metrics"]
        print(
            "{name}: recall={recall:.4f} precision={precision:.4f} hit_rate={hit_rate:.4f} "
            "mrr={mrr:.4f} ndcg={ndcg:.4f}".format(
                name=report["config_name"],
                recall=metrics["recall_at_k"],
                precision=metrics["precision_at_k"],
                hit_rate=metrics["hit_rate_at_k"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg_at_k"],
            )
        )
    if args.require_llm_validation and llm_validation["status"] != "passed":
        return 2
    return 0


def run_suite_evaluation(
    run: dict[str, str],
    eval_file: Path,
    top_k: int,
    output_dir: Path,
) -> dict[str, Any]:
    """Run one retrieval-only evaluation and persist its detailed outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = resolve_project_path(run["config"])
    config = load_rag_config(config_path)
    validate_retrieval_storage(config)
    questions = load_questions(eval_file)
    samples = [evaluate_question(row, top_k, config_path=config_path) for row in questions]
    metrics = summarize(samples, top_k)
    retrieval_metadata = get_retrieval_metadata(config, top_k)
    report = {
        "suite_id": run["id"],
        "suite_label": run["label"],
        "config_name": str(config.get("name") or config_path.stem),
        "git_commit": get_git_commit(),
        "top_k": top_k,
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
    write_json(output_dir / "rag_eval.json", report)
    (output_dir / "rag_eval.md").write_text(render_markdown_report(report), encoding="utf-8")
    return report


def run_llm_validation(question: str, config_path: str, top_k: int) -> dict[str, Any]:
    """Run one representative RAG answer generation with the configured LLM."""
    resolved_config_path = resolve_project_path(config_path)
    config = load_rag_config(resolved_config_path)
    try:
        documents = run_configured_retriever(question, top_k, config, resolved_config_path)
        result = generate_answer(question, documents, config)
    except Exception as exc:
        return {
            "status": "failed",
            "question": question,
            "answer_preview": "",
            "cited_sources": [],
            "error": str(exc),
        }
    return {
        "status": "passed",
        "question": question,
        "answer_preview": result.answer[:800],
        "cited_sources": result.cited_sources,
        "error": "",
    }


def render_optimization_report(reports: list[dict[str, Any]], llm_validation: dict[str, Any]) -> str:
    """Render the suite-level RAG optimization report."""
    by_id = {report["suite_id"]: report for report in reports}
    dense = by_id["dense_character"]
    hybrid = by_id["hybrid_character"]
    rerank = by_id["hybrid_rerank_character"]
    markdown = by_id["hybrid_rerank_markdown"]
    retrieval_delta = compare_metrics(dense["metrics"], rerank["metrics"], RETRIEVAL_SIGNIFICANT_THRESHOLD)
    chunking_delta = compare_metrics(rerank["metrics"], markdown["metrics"], CHUNKING_SIGNIFICANT_THRESHOLD)

    lines = [
        "# RAG Optimization Report",
        "",
        "## Summary",
        "",
        "- Benchmark type: retrieval-only metrics plus one representative LLM call validation.",
        "- Stress corpus: production docs plus transparent low-density noise docs.",
        f"- Retrieval mode significant improvement: `{format_pass(retrieval_delta['significant'])}`.",
        f"- Chunking significant improvement: `{format_pass(chunking_delta['significant'])}`.",
        f"- LLM validation: `{llm_validation['status']}`.",
        "",
        "## Overall Metrics",
        "",
        "| Stage | Config | Chunking | Recall@k | Precision@k | Hit Rate@k | MRR | NDCG@k | Failed |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in reports:
        metrics = report["metrics"]
        chunking = report.get("config", {}).get("chunking", {})
        lines.append(
            "| {label} | {config} | {chunking} | {recall:.4f} | {precision:.4f} | {hit_rate:.4f} | "
            "{mrr:.4f} | {ndcg:.4f} | {failed} |".format(
                label=report["suite_label"],
                config=report["config_name"],
                chunking=chunking.get("strategy", "character") if isinstance(chunking, dict) else "character",
                recall=metrics["recall_at_k"],
                precision=metrics["precision_at_k"],
                hit_rate=metrics["hit_rate_at_k"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg_at_k"],
                failed=metrics["failed_count"],
            )
        )

    lines.extend(
        [
            "",
            "## Growth Analysis",
            "",
            "| Comparison | Recall Delta | Precision Delta | Hit Rate Delta | MRR Delta | NDCG Delta | Failed Delta | Significant |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            render_delta_row("Dense -> Hybrid", compare_metrics(dense["metrics"], hybrid["metrics"], RETRIEVAL_SIGNIFICANT_THRESHOLD)),
            render_delta_row("Hybrid -> Hybrid + Reranker", compare_metrics(hybrid["metrics"], rerank["metrics"], RETRIEVAL_SIGNIFICANT_THRESHOLD)),
            render_delta_row("Dense -> Hybrid + Reranker", retrieval_delta),
            render_delta_row("Character -> Markdown-aware", chunking_delta),
            "",
            "## Metrics By Category",
            "",
        ]
    )
    lines.extend(render_grouped_metrics(reports, "by_category", "Category"))
    lines.extend(["", "## Metrics By Difficulty", ""])
    lines.extend(render_grouped_metrics(reports, "by_difficulty", "Difficulty"))
    lines.extend(["", "## Failed Samples Comparison", ""])
    lines.extend(render_failed_samples(reports))
    lines.extend(["", "## Reranker And Chunking Evidence", ""])
    lines.extend(render_rerank_example(rerank))
    lines.extend(render_markdown_chunk_example(markdown))
    lines.extend(["", "## LLM Validation", ""])
    lines.extend(render_llm_validation(llm_validation))
    return "\n".join(lines) + "\n"


def compare_metrics(before: dict[str, Any], after: dict[str, Any], threshold: float) -> dict[str, Any]:
    """Compare two metric summaries and decide whether the improvement is significant."""
    deltas = {
        "recall_at_k": float(after["recall_at_k"]) - float(before["recall_at_k"]),
        "precision_at_k": float(after["precision_at_k"]) - float(before["precision_at_k"]),
        "hit_rate_at_k": float(after["hit_rate_at_k"]) - float(before["hit_rate_at_k"]),
        "mrr": float(after["mrr"]) - float(before["mrr"]),
        "ndcg_at_k": float(after["ndcg_at_k"]) - float(before["ndcg_at_k"]),
        "failed_count": int(after["failed_count"]) - int(before["failed_count"]),
    }
    significant = (
        (deltas["mrr"] >= threshold or deltas["ndcg_at_k"] >= threshold)
        and deltas["hit_rate_at_k"] >= 0
        and deltas["failed_count"] <= 0
    )
    return {**deltas, "significant": significant}


def render_delta_row(label: str, delta: dict[str, Any]) -> str:
    """Render one growth comparison row."""
    return (
        f"| {label} | {delta['recall_at_k']:+.4f} | {delta['precision_at_k']:+.4f} | "
        f"{delta['hit_rate_at_k']:+.4f} | {delta['mrr']:+.4f} | {delta['ndcg_at_k']:+.4f} | "
        f"{delta['failed_count']:+d} | {format_pass(bool(delta['significant']))} |"
    )


def render_grouped_metrics(reports: list[dict[str, Any]], field: str, label: str) -> list[str]:
    """Render category or difficulty grouped metrics."""
    lines = [
        f"| {label} | Stage | Recall | Precision | Hit Rate | MRR | NDCG |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    group_names = sorted(
        {
            group
            for report in reports
            for group in report["metrics"].get(field, {})
        }
    )
    for group in group_names:
        for report in reports:
            metrics = report["metrics"].get(field, {}).get(group)
            if not metrics:
                continue
            lines.append(
                f"| {group} | {report['suite_id']} | {metrics['recall_at_k']:.4f} | "
                f"{metrics['precision_at_k']:.4f} | {metrics['hit_rate_at_k']:.4f} | "
                f"{metrics['mrr']:.4f} | {metrics['ndcg_at_k']:.4f} |"
            )
    return lines


def render_failed_samples(reports: list[dict[str, Any]]) -> list[str]:
    """Render failed sample ids for each run."""
    lines = ["| Stage | Failed Count | Failed Sample IDs |", "| --- | ---: | --- |"]
    for report in reports:
        failed_ids = [sample["id"] for sample in report["samples"] if sample["hit_count"] == 0]
        lines.append(f"| {report['suite_id']} | {len(failed_ids)} | {', '.join(failed_ids) or '(none)'} |")
    return lines


def render_rerank_example(report: dict[str, Any]) -> list[str]:
    """Render a compact example showing reranker metadata."""
    for sample in report["samples"]:
        for item in sample.get("retrieved", []):
            metadata = item.get("metadata", {})
            if metadata.get("rerank_score") is not None:
                return [
                    "### Reranker Example",
                    "",
                    f"- Question: {sample['question']}",
                    f"- Top source: `{item['source']}`",
                    f"- Rerank score: `{metadata.get('rerank_score')}`",
                    f"- Original rank: `{metadata.get('original_rank')}`",
                    f"- Final rank: `{metadata.get('final_rank')}`",
                ]
    return ["### Reranker Example", "", "No rerank metadata was found in the top results."]


def render_markdown_chunk_example(report: dict[str, Any]) -> list[str]:
    """Render a compact markdown-aware chunk metadata example."""
    for sample in report["samples"]:
        for item in sample.get("retrieved", []):
            heading_path = item.get("metadata", {}).get("heading_path")
            if heading_path:
                return [
                    "### Markdown-aware Chunk Example",
                    "",
                    f"- Question: {sample['question']}",
                    f"- Source: `{item['source']}`",
                    f"- Heading path: `{heading_path}`",
                    f"- Preview: {item['content_preview']}",
                ]
    return ["### Markdown-aware Chunk Example", "", "No heading_path metadata was found in the top results."]


def render_llm_validation(validation: dict[str, Any]) -> list[str]:
    """Render representative LLM call validation."""
    lines = [
        f"- Status: `{validation['status']}`",
        f"- Question: {validation['question']}",
    ]
    if validation["cited_sources"]:
        lines.append(f"- Cited sources: {' '.join(validation['cited_sources'])}")
    if validation["answer_preview"]:
        lines.extend(["", "Answer preview:", "", validation["answer_preview"]])
    if validation["error"]:
        lines.append(f"- Error: `{validation['error']}`")
    return lines


def format_pass(value: bool) -> str:
    """Format a boolean pass/fail flag."""
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
