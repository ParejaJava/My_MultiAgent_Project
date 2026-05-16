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
