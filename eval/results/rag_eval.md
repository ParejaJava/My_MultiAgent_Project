# RAG Retrieval Evaluation

## Run Metadata

- Config: `baseline_hash`
- Git commit: `6c3a65736879457ce9d03bd2391b1caf1294bc79`
- Eval file: `eval/questions.jsonl`
- Top K: `5`
- Timestamp: `2026-05-16T15:21:12.286066+00:00`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Total Questions | 21 |
| Recall@5 | 0.0000 |
| Precision@5 | 0.0000 |
| Hit Rate@5 | 0.0000 |
| MRR | 0.0000 |
| NDCG@5 | 0.0000 |
| Failed Samples | 21 |

## Metrics By Category

| Category | Count | Recall | Precision | Hit Rate | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cache | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| database | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| message-queue | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| object-storage | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| realtime | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| retrieval | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| traffic | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Failed Samples

### minio-001
- Category: object-storage
- Difficulty: easy
- Question: MinIO 分片上传最后合并时报 400 InvalidPartOrder，应该检查什么？
- Expected sources: data/docs/minio_multipart_resume.md
- Retrieved sources: (none)
- Expected keywords: InvalidPartOrder, CompleteMultipartUpload, partNumber, ETag, 升序

### minio-002
- Category: object-storage
- Difficulty: medium
- Question: 大文件传着传着就没了，刷新以后又从头开始，感觉断点续传没生效，这是哪块的问题？
- Expected sources: data/docs/minio_multipart_resume.md
- Retrieved sources: (none)
- Expected keywords: 断点续传, uploadId, fileHash, ListParts, NoSuchUpload

### minio-003
- Category: object-storage
- Difficulty: hard
- Question: 日志里有 413 Payload Too Large 和 504 Gateway Timeout，MinIO 大文件上传应该如何处理和预防？
- Expected sources: data/docs/gateway_high_concurrency.md, data/docs/minio_multipart_resume.md
- Retrieved sources: (none)
- Expected keywords: 413, 504, client_max_body_size, proxy_read_timeout, 分片上传, 预签名 URL

### redis-001
- Category: cache
- Difficulty: easy
- Question: Redis 报 READONLY You can't write against a read only replica，是什么原因？
- Expected sources: data/docs/redis_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: READONLY, replica, 主从切换, 拓扑刷新, 连接池

### redis-002
- Category: cache
- Difficulty: medium
- Question: 接口突然慢了，Redis 好像也没挂，就是偶尔超时，这种咋查？
- Expected sources: data/docs/redis_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: Redis command timed out, SLOWLOG, 大 key, BUSY, latency

### redis-003
- Category: cache
- Difficulty: hard
- Question: Redis 日志出现 OOM command not allowed when used memory > maxmemory，如何解决并预防？
- Expected sources: data/docs/redis_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: OOM command not allowed, used_memory, maxmemory, evicted_keys, TTL, 大 key

### rabbitmq-001
- Category: message-queue
- Difficulty: easy
- Question: RabbitMQ 队列 messages_ready 一直涨，消费者看起来处理不过来，怎么排查？
- Expected sources: data/docs/rabbitmq_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: messages_ready, consumer count, ack rate, publish rate, prefetch

### rabbitmq-002
- Category: message-queue
- Difficulty: medium
- Question: MQ 堆住了，业务消息半天不动，也不知道是消费者死了还是 RabbitMQ 出问题了。
- Expected sources: data/docs/rabbitmq_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 消息堆积, messages_unacknowledged, consumer count 0, consumer_timeout, ack

### rabbitmq-003
- Category: message-queue
- Difficulty: hard
- Question: 启动消费者时报 406 PRECONDITION_FAILED inequivalent arg，怎么解决？
- Expected sources: data/docs/rabbitmq_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 406 PRECONDITION_FAILED, inequivalent arg, durable, x-dead-letter-exchange, 队列声明

### mysql-001
- Category: database
- Difficulty: easy
- Question: MySQL 报 1205 Lock wait timeout exceeded，应该怎么定位？
- Expected sources: data/docs/mysql_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 1205, ER_LOCK_WAIT_TIMEOUT, Lock wait timeout exceeded, innodb_trx, 长事务

### mysql-002
- Category: database
- Difficulty: medium
- Question: 数据库最近有点卡，接口偶尔超时，但没明显报错，先看哪里？
- Expected sources: data/docs/mysql_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 慢 SQL, EXPLAIN, SHOW PROCESSLIST, Using filesort, Using temporary

### mysql-003
- Category: database
- Difficulty: hard
- Question: 日志中同时出现 1213 Deadlock found 和 1062 Duplicate entry，消费端写 MySQL 应如何处理？
- Expected sources: data/docs/mysql_ops_diagnosis.md, data/docs/rabbitmq_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 1213, ER_LOCK_DEADLOCK, 1062, ER_DUP_ENTRY, 幂等, 重复消费

### websocket-001
- Category: realtime
- Difficulty: easy
- Question: WebSocket 建连失败，网关返回 426 Upgrade Required，应该检查哪些配置？
- Expected sources: data/docs/websocket_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 426 Upgrade Required, Upgrade, Connection, Sec-WebSocket-Key, 握手失败

### websocket-002
- Category: realtime
- Difficulty: medium
- Question: 前端说连接一会儿就断，刷新又好了，这种 WebSocket 问题怎么查？
- Expected sources: data/docs/websocket_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: 1006, ECONNRESET, idle timeout, heartbeat, 断线重连

### websocket-003
- Category: realtime
- Difficulty: hard
- Question: 多实例部署后 WebSocket 只给部分用户推送成功，如何解决和预防？
- Expected sources: data/docs/websocket_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: session not found, broadcast miss, Redis pubsub, RabbitMQ consumer cancelled, 粘性会话

### rag-001
- Category: retrieval
- Difficulty: easy
- Question: RAG 查询返回 retrieved_docs=[]，应该先排查什么？
- Expected sources: data/docs/rag_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: retrieved_docs=[], CollectionNotFound, collection count, VECTOR_STORE_PATH, ingest

### rag-002
- Category: retrieval
- Difficulty: medium
- Question: 问的问题明明在文档里，但搜出来的内容很奇怪，不太相关，这是 RAG 哪块不行？
- Expected sources: data/docs/rag_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: irrelevant retrieval, low score, chunk too large, BM25, rerank

### rag-003
- Category: retrieval
- Difficulty: hard
- Question: Chroma 报 sqlite disk I/O error 或 InvalidDimension，分别应该如何处理？
- Expected sources: data/docs/rag_ops_diagnosis.md
- Retrieved sources: (none)
- Expected keywords: sqlite disk I/O error, InvalidDimension, chroma.sqlite3, embedding dimension, 重建索引

### gateway-001
- Category: traffic
- Difficulty: easy
- Question: 网关返回 504 Gateway Timeout，如何判断是网关问题还是后端慢？
- Expected sources: data/docs/gateway_high_concurrency.md
- Retrieved sources: (none)
- Expected keywords: 504 Gateway Timeout, upstream timed out, P95, P99, trace id, 慢 SQL

### gateway-002
- Category: traffic
- Difficulty: medium
- Question: 高峰期用户说系统卡死，有时候 502 有时候 503，还有些请求直接没响应，先怎么查？
- Expected sources: data/docs/gateway_high_concurrency.md
- Retrieved sources: (none)
- Expected keywords: 502, 503, 499, 线程池, 连接池, no healthy upstream

### gateway-003
- Category: traffic
- Difficulty: hard
- Question: 如何预防高并发下 429、503、线程池耗尽和连接池 pending？
- Expected sources: data/docs/gateway_high_concurrency.md
- Retrieved sources: (none)
- Expected keywords: 429, 503, RejectedExecutionException, pending acquire timeout, 限流, 熔断, 有界队列

