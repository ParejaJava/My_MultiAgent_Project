# RAG Retrieval Evaluation

## Run Metadata

- Config: `hybrid_rrf_rerank_stress_markdown`
- Git commit: `56f238d23e5436405ce1d6b93eaa5815ea4d02c5`
- Eval file: `D:/Work/AgentProject2026/eval/questions_stress.jsonl`
- Top K: `5`
- Retriever: `hybrid_rrf`
- Retrieve top N: `40`
- Rerank top K: `5`
- Reranker: `bge`
- Reranker model: `D:/AgentData/Models/bge-reranker-base`
- Timestamp: `2026-05-25T15:17:27.526932+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 30 |
| Recall@5 | 1.0000 |
| Precision@5 | 0.4000 |
| Hit Rate@5 | 1.0000 |
| MRR | 1.0000 |
| NDCG@5 | 0.9829 |
| Failed Samples | 0 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| signature-auth | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cache | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-cdn | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-database | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-gateway | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-object | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |
| signature-queue | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9323 |
| signature-rag | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9501 |
| signature-scheduler | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.9732 |
| signature-websocket | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 1.0000 |

## Failed Samples

No failed samples.
