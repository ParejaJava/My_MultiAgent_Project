# RAG Run Comparison

| Run | Config | Top K | Eval File | Timestamp | Recall@k | Precision@k | Hit Rate@k | MRR | NDCG@k | Git Commit |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| eval/results/rag_eval.json | baseline_hash | 5 | eval/questions.jsonl | 2026-05-16T15:21:12.286066+00:00 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 6c3a65736879 |
| eval/results/hybrid_hash_rrf/rag_eval.json | hybrid_hash_rrf | 5 | eval/questions.jsonl | 2026-05-16T15:31:42.673649+00:00 | 0.8810 | 0.1905 | 0.9048 | 0.9048 | 0.8863 | 6c3a65736879 |
