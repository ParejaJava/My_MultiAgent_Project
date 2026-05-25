# RAG Retrieval Evaluation

## Run Metadata

- Config: `hybrid_bge_rrf_stress_character`
- Git commit: `56f238d23e5436405ce1d6b93eaa5815ea4d02c5`
- Eval file: `D:/Work/AgentProject2026/eval/questions_stress.jsonl`
- Top K: `5`
- Retriever: `hybrid_rrf`
- Retrieve top N: `30`
- Rerank top K: `5`
- Reranker: `none`
- Reranker model: `none`
- Timestamp: `2026-05-25T15:13:24.039885+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 30 |
| Recall@5 | 0.9000 |
| Precision@5 | 0.3600 |
| Hit Rate@5 | 1.0000 |
| MRR | 1.0000 |
| NDCG@5 | 0.8649 |
| Failed Samples | 0 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| signature-auth | 3 | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.7713 |
| signature-cache | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9056 |
| signature-cdn | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-database | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7153 |
| signature-gateway | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9323 |
| signature-object | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-queue | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9092 |
| signature-rag | 3 | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.7944 |
| signature-scheduler | 3 | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8034 |
| signature-websocket | 3 | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8443 |

## Failed Samples

No failed samples.
