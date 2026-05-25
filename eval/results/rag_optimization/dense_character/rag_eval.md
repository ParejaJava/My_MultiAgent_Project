# RAG Retrieval Evaluation

## Run Metadata

- Config: `bge_local_stress_character`
- Git commit: `56f238d23e5436405ce1d6b93eaa5815ea4d02c5`
- Eval file: `D:/Work/AgentProject2026/eval/questions_stress.jsonl`
- Top K: `5`
- Retriever: `chroma_dense`
- Retrieve top N: `20`
- Rerank top K: `5`
- Reranker: `none`
- Reranker model: `none`
- Timestamp: `2026-05-25T15:13:10.159150+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 30 |
| Recall@5 | 0.7333 |
| Precision@5 | 0.2933 |
| Hit Rate@5 | 1.0000 |
| MRR | 1.0000 |
| NDCG@5 | 0.7438 |
| Failed Samples | 0 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| signature-auth | 3 | 0.5000 | 0.2000 | 1.0000 | 1.0000 | 0.6131 |
| signature-cache | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8683 |
| signature-cdn | 3 | 1.0000 | 0.4000 | 1.0000 | 1.0000 | 0.8914 |
| signature-database | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |
| signature-gateway | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7421 |
| signature-object | 3 | 0.8333 | 0.3333 | 1.0000 | 1.0000 | 0.8034 |
| signature-queue | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7421 |
| signature-rag | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |
| signature-scheduler | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.7012 |
| signature-websocket | 3 | 0.6667 | 0.2667 | 1.0000 | 1.0000 | 0.6922 |

## Failed Samples

No failed samples.
