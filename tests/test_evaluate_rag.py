from pathlib import Path

import pytest

from scripts.evaluate_rag import (
    load_config,
    ndcg_at_k,
    precision_at_k,
    rank_relevance,
    recall_at_k,
    reciprocal_rank,
    summarize,
)
from scripts.compare_rag_runs import render_comparison
from scripts.evaluate_rag_suite import compare_metrics, render_optimization_report


def test_recall_and_precision_at_k() -> None:
    retrieved = ["data/docs/redis_ops_diagnosis.md", "data/docs/mysql_ops_diagnosis.md"]
    relevant = {"data/docs/redis_ops_diagnosis.md", "data/docs/rabbitmq_ops_diagnosis.md"}

    assert recall_at_k(retrieved, relevant) == 0.5
    assert precision_at_k(retrieved, relevant, top_k=3) == pytest.approx(1 / 3)


def test_rank_relevance_counts_duplicate_source_once() -> None:
    retrieved = [
        "data/docs/redis_ops_diagnosis.md",
        "data/docs/redis_ops_diagnosis.md",
        "data/docs/mysql_ops_diagnosis.md",
    ]
    relevant = {"data/docs/redis_ops_diagnosis.md", "data/docs/mysql_ops_diagnosis.md"}

    assert rank_relevance(retrieved, relevant) == [1, 0, 1]


def test_reciprocal_rank() -> None:
    assert reciprocal_rank([0, 0, 1]) == pytest.approx(1 / 3)
    assert reciprocal_rank([0, 0, 0]) == 0.0


def test_ndcg_at_k() -> None:
    assert ndcg_at_k([1, 0, 1], ideal_relevant_count=2) == pytest.approx(
        (1 + 1 / 2) / (1 + 1 / 1.584962500721156)
    )
    assert ndcg_at_k([], ideal_relevant_count=0) == 0.0


def test_summarize_metrics() -> None:
    samples = [
        {
            "category": "cache",
            "difficulty": "easy",
            "hit_count": 1,
            "recall_at_k": 1.0,
            "precision_at_k": 0.5,
            "hit_rate_at_k": 1.0,
            "rr": 1.0,
            "ndcg_at_k": 1.0,
        },
        {
            "category": "cache",
            "difficulty": "hard",
            "hit_count": 0,
            "recall_at_k": 0.0,
            "precision_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "rr": 0.0,
            "ndcg_at_k": 0.0,
        },
    ]

    summary = summarize(samples, top_k=2)

    assert summary["total_questions"] == 2
    assert summary["failed_count"] == 1
    assert summary["recall_at_k"] == 0.5
    assert summary["by_category"]["cache"]["count"] == 2


def test_load_baseline_config() -> None:
    config = load_config(Path("configs/rag/baseline_hash.yaml"))

    assert config["name"] == "baseline_hash"
    assert config["retriever"] == "dense"


def test_render_rag_run_comparison() -> None:
    markdown = render_comparison(
        [
            {
                "file": "eval/results/rag_eval.json",
                "config_name": "baseline_hash",
                "git_commit": "abcdef1234567890",
                "top_k": 5,
                "eval_file": "eval/questions.jsonl",
                "timestamp": "2026-05-16T00:00:00+00:00",
                "metrics": {
                    "recall_at_k": 0.5,
                    "precision_at_k": 0.2,
                    "hit_rate_at_k": 0.8,
                    "mrr": 0.7,
                    "ndcg_at_k": 0.6,
                },
            }
        ]
    )

    assert "Recall@k" in markdown
    assert "baseline_hash" in markdown
    assert "0.5000" in markdown


def test_compare_metrics_detects_significant_growth() -> None:
    before = {
        "recall_at_k": 0.4,
        "precision_at_k": 0.2,
        "hit_rate_at_k": 0.7,
        "mrr": 0.3,
        "ndcg_at_k": 0.35,
        "failed_count": 3,
    }
    after = {
        "recall_at_k": 0.6,
        "precision_at_k": 0.3,
        "hit_rate_at_k": 0.8,
        "mrr": 0.45,
        "ndcg_at_k": 0.5,
        "failed_count": 2,
    }

    delta = compare_metrics(before, after, threshold=0.10)

    assert delta["mrr"] == pytest.approx(0.15)
    assert delta["significant"] is True


def test_render_optimization_report_contains_retrieval_and_chunking_sections() -> None:
    reports = [
        make_suite_report("dense_character", "Dense", "dense", "character", mrr=0.2, ndcg=0.2, failed=3),
        make_suite_report("hybrid_character", "Hybrid", "hybrid", "character", mrr=0.35, ndcg=0.35, failed=2),
        make_suite_report("hybrid_rerank_character", "Rerank", "rerank", "character", mrr=0.5, ndcg=0.5, failed=1),
        make_suite_report("hybrid_rerank_markdown", "Markdown", "markdown", "markdown", mrr=0.6, ndcg=0.58, failed=1),
    ]

    markdown = render_optimization_report(
        reports,
        {
            "status": "passed",
            "question": "Redis READONLY 怎么处理？",
            "answer_preview": "answer",
            "cited_sources": ["[source: data/docs/redis_ops_diagnosis.md#chunk_1]"],
            "error": "",
        },
    )

    assert "Dense -> Hybrid + Reranker" in markdown
    assert "Character -> Markdown-aware" in markdown
    assert "Markdown-aware Chunk Example" in markdown
    assert "LLM Validation" in markdown
    assert "`passed`" in markdown


def make_suite_report(
    suite_id: str,
    label: str,
    config_name: str,
    chunking_strategy: str,
    mrr: float,
    ndcg: float,
    failed: int,
) -> dict:
    return {
        "suite_id": suite_id,
        "suite_label": label,
        "config_name": config_name,
        "config": {"chunking": {"strategy": chunking_strategy}},
        "metrics": {
            "recall_at_k": 0.7,
            "precision_at_k": 0.3,
            "hit_rate_at_k": 0.8,
            "mrr": mrr,
            "ndcg_at_k": ndcg,
            "failed_count": failed,
            "by_category": {"cache": {"recall_at_k": 0.7, "precision_at_k": 0.3, "hit_rate_at_k": 0.8, "mrr": mrr, "ndcg_at_k": ndcg}},
            "by_difficulty": {"easy": {"recall_at_k": 0.7, "precision_at_k": 0.3, "hit_rate_at_k": 0.8, "mrr": mrr, "ndcg_at_k": ndcg}},
        },
        "samples": [
            {
                "id": f"{suite_id}-sample",
                "question": "Redis READONLY 怎么处理？",
                "hit_count": 1,
                "retrieved": [
                    {
                        "source": "data/docs/redis_ops_diagnosis.md",
                        "metadata": {
                            "rerank_score": 0.9 if "rerank" in suite_id else None,
                            "original_rank": 2,
                            "final_rank": 1,
                            "heading_path": "Redis > READONLY" if chunking_strategy == "markdown" else None,
                        },
                        "content_preview": "READONLY replica write failure.",
                    }
                ],
            }
        ],
    }
