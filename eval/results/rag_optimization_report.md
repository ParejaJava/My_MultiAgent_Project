# RAG Optimization Report

## Summary

- Benchmark type: retrieval-only metrics plus one representative LLM call validation.
- Stress corpus: production docs plus transparent low-density noise docs.
- Retrieval mode significant improvement: `yes`.
- Chunking significant improvement: `yes`.
- LLM validation: `skipped`.

## Overall Metrics

| Stage | Config | Chunking | Recall@k | Precision@k | Hit Rate@k | MRR | NDCG@k | Failed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dense BGE + character chunking | bge_local_stress_character | character | 0.7333 | 0.2933 | 1.0000 | 1.0000 | 0.7438 | 0 |
| Hybrid BGE + BM25 + character chunking | hybrid_bge_rrf_stress_character | character | 0.9000 | 0.3600 | 1.0000 | 1.0000 | 0.8649 | 0 |
| Hybrid BGE + BM25 + BGE reranker + character chunking | hybrid_rrf_rerank_stress_character | character | 0.9500 | 0.3800 | 1.0000 | 0.9667 | 0.9093 | 0 |
| Hybrid BGE + BM25 + BGE reranker + markdown-aware chunking | hybrid_rrf_rerank_stress_markdown | markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9829 | 0 |

## Growth Analysis

| Comparison | Recall Delta | Precision Delta | Hit Rate Delta | MRR Delta | NDCG Delta | Failed Delta | Significant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Dense -> Hybrid | +0.1667 | +0.0667 | +0.0000 | +0.0000 | +0.1211 | +0 | yes |
| Hybrid -> Hybrid + Reranker | +0.0500 | +0.0200 | +0.0000 | -0.0333 | +0.0444 | +0 | no |
| Dense -> Hybrid + Reranker | +0.2167 | +0.0867 | +0.0000 | -0.0333 | +0.1655 | +0 | yes |
| Character -> Markdown-aware | +0.0500 | +0.0200 | +0.0000 | +0.0333 | +0.0736 | +0 | yes |

## Metrics By Category

| Category | Stage | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| signature-auth | dense_character | 0.5000 | 0.2000 | 1.0000 | 1.0000 | 0.6131 |
| signature-auth | hybrid_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.7713 |
| signature-auth | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-auth | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cache | dense_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8683 |
| signature-cache | hybrid_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9056 |
| signature-cache | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 0.6667 | 0.7547 |
| signature-cache | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cdn | dense_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8914 |
| signature-cdn | hybrid_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cdn | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cdn | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-database | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |
| signature-database | hybrid_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7153 |
| signature-database | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-database | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-gateway | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7421 |
| signature-gateway | hybrid_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9323 |
| signature-gateway | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9591 |
| signature-gateway | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-object | dense_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8034 |
| signature-object | hybrid_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-object | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9465 |
| signature-object | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-queue | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7421 |
| signature-queue | hybrid_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9092 |
| signature-queue | hybrid_rerank_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8710 |
| signature-queue | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9323 |
| signature-rag | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |
| signature-rag | hybrid_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.7944 |
| signature-rag | hybrid_rerank_character | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9234 |
| signature-rag | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9501 |
| signature-scheduler | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7012 |
| signature-scheduler | hybrid_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8034 |
| signature-scheduler | hybrid_rerank_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8710 |
| signature-scheduler | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-websocket | dense_character | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |
| signature-websocket | hybrid_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8443 |
| signature-websocket | hybrid_rerank_character | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8212 |
| signature-websocket | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |

## Metrics By Difficulty

| Difficulty | Stage | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| hard | dense_character | 0.7333 | 0.2933 | 1.0000 | 1.0000 | 0.7438 |
| hard | hybrid_character | 0.9000 | 0.3600 | 1.0000 | 1.0000 | 0.8649 |
| hard | hybrid_rerank_character | 0.9500 | 0.3800 | 1.0000 | 0.9667 | 0.9093 |
| hard | hybrid_rerank_markdown | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9829 |

## Failed Samples Comparison

| Stage | Failed Count | Failed Sample IDs |
| --- | ---: | --- |
| dense_character | 0 | (none) |
| hybrid_character | 0 | (none) |
| hybrid_rerank_character | 0 | (none) |
| hybrid_rerank_markdown | 0 | (none) |

## Reranker And Chunking Evidence

### Reranker Example

- Question: RXA-1001 appears during cache write operations. Which runbook should be used?
- Top source: `data/docs_stress_noise/signature_lure_index_01.md`
- Rerank score: `3.245025634765625`
- Original rank: `2`
- Final rank: `1`
### Markdown-aware Chunk Example

- Question: RXA-1001 appears during cache write operations. Which runbook should be used?
- Source: `data/docs_stress_cases/signature_action_matrix.md`
- Heading path: `Signature Action Matrix`
- Preview: | Signature | Action Key |
| --- | --- |
| RXA-1001 RXA-1001 RXA-1001 | topology-cache-reconnect-primary cache write runbook |
| RXA-1002 RXA-1002 RXA-1002 | memory-eviction-ttl-large-key cache eviction guidance |
| RXA-1003 RXA-1003 RXA-10

## LLM Validation

- Status: `skipped`
- Question: Redis READONLY 怎么处理？
