# RAG Retrieval Evaluation

## Run Metadata

- Config: `hybrid_hash_rrf`
- Git commit: `6c3a65736879457ce9d03bd2391b1caf1294bc79`
- Eval file: `eval/questions.jsonl`
- Top K: `5`
- Timestamp: `2026-05-16T15:31:42.673649+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 21 |
| Recall@5 | 0.8810 |
| Precision@5 | 0.1905 |
| Hit Rate@5 | 0.9048 |
| MRR | 0.9048 |
| NDCG@5 | 0.8863 |
| Failed Samples | 2 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cache | 3 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 |
| database | 3 | 0.5000 | 0.1333 | 0.6667 | 0.6667 | 0.5377 |
| message-queue | 3 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 |
| object-storage | 3 | 0.6667 | 0.2000 | 0.6667 | 0.6667 | 0.6667 |
| realtime | 3 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 |
| retrieval | 3 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 |
| traffic | 3 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 |

## Failed Samples

### minio-002
- Category: object-storage
- Difficulty: medium
- Question: 大文件传着传着就没了，刷新以后又从头开始，感觉断点续传没生效，这是哪块的问题？
- Expected sources: data/docs/minio_multipart_resume.md
- Retrieved sources: (none)
- Expected keywords: 断点续传, uploadId, fileHash, ListParts, NoSuchUpload

### mysql-002
- Category: database
- Difficulty: medium
- Question: 数据库最近有点卡，接口偶尔超时，但没明显报错，先看哪里？
- Expected sources: data/docs/mysql_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 慢 SQL, EXPLAIN, SHOW PROCESSLIST, Using filesort, Using temporary

