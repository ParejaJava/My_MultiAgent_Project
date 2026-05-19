# RAG Retrieval Evaluation

## Run Metadata

- Config: `hybrid_bge_rrf`
- Git commit: `edfb24c65297555c6a7f883cbd9068ea1858f5e8`
- Eval file: `D:/Work/AgentProject2026/eval/questions.jsonl`
- Top K: `3`
- Retriever: `hybrid_rrf`
- Retrieve top N: `10`
- Rerank top K: `3`
- Reranker: `none`
- Reranker model: `none`
- Timestamp: `2026-05-18T15:14:24.768587+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 21 |
| Recall@3 | 0.9762 |
| Precision@3 | 0.3492 |
| Hit Rate@3 | 1.0000 |
| MRR | 0.9444 |
| NDCG@3 | 0.9402 |
| Failed Samples | 0 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cache | 3 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| database | 3 | 0.8333 | 0.3333 | 1.0000 | 0.7778 | 0.7044 |
| message-queue | 3 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| object-storage | 3 | 1.0000 | 0.4444 | 1.0000 | 1.0000 | 1.0000 |
| realtime | 3 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| retrieval | 3 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| traffic | 3 | 1.0000 | 0.3333 | 1.0000 | 0.8333 | 0.8770 |

## Failed Samples

No failed samples.
