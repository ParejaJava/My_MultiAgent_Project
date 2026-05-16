---
title: RAG 系统运维诊断知识库
category: retrieval
service: RAG
severity: medium
tags:
  - rag
  - embedding
  - chroma
  - vector-store
  - retrieval
  - chunking
  - metadata
  - bm25
error_codes:
  - CollectionNotFound
  - InvalidDimension
  - empty retrieval
  - no relevant documents
  - metadata missing
  - sqlite disk I/O error
  - 400
  - 404
  - 500
---

# RAG 系统运维诊断知识库

## Metadata
- component: RAG
- category: retrieval
- tags: rag, embedding, chroma, vector store, retrieval, chunking, metadata, bm25
- common_errors: CollectionNotFound, InvalidDimension, empty retrieval, no relevant documents, metadata missing, sqlite disk I/O error, 400, 404, 500

## Overview
RAG 系统通常包括文档加载、切分、embedding、向量库入库、检索、重排和答案生成。常见故障包括文档未入库、检索为空、结果不相关、embedding 维度不一致、metadata 丢失、向量库持久化失败和 chunk 设计不合理。

## Symptoms

### 检索结果为空 empty retrieval
- 表现: 用户问题明确，但 Retrieval Agent 返回空 evidence。
- 错误码/日志关键词: `empty retrieval`, `CollectionNotFound`, `collection does not exist`, `No documents found`, `retrieved_docs=[]`, `404 collection`
- 相关指标: collection count, ingest chunk count, query count, hit rate。
- 可能原因: 未执行入库脚本，collection 名称不一致，persist directory 配置错误，query 过短，metadata filter 过严。
- 排查步骤: 检查 Chroma collection count；确认 `VECTOR_STORE_PATH`；执行 ingest 脚本；打印 query 和 top_k；取消 metadata filter 测试。
- 修复建议: 启动前检查索引是否存在；统一 collection name；入库后记录 chunk 数；query 增强和同义词扩展。

### 检索结果不相关
- 表现: 返回了文档，但内容和问题无关，Diagnosis Agent 可能引用错误证据。
- 错误码/日志关键词: `no relevant documents`, `low score`, `irrelevant retrieval`, `hallucinated evidence`, `score below threshold`
- 相关指标: similarity score, overlap terms, rerank score, 用户反馈命中率。
- 可能原因: embedding 质量不足，chunk 太大混入多个主题，chunk 太小缺上下文，缺少 BM25 关键词召回，top_k 太大。
- 排查步骤: 打印 query、score、source、chunk content；检查 chunk 标题是否包含错误码；比较向量召回和关键词召回结果。
- 修复建议: 使用混合检索 BM25 + vector；增加 score threshold；按 Markdown 标题切分；加入 rerank；控制 top_k。

### Embedding 维度不一致 InvalidDimension
- 表现: 入库或查询时报维度错误。
- 错误码/日志关键词: `InvalidDimension`, `Embedding dimension`, `dimension mismatch`, `expected dimension`, `got dimension`
- 相关指标: embedding model name, vector dimension, collection metadata。
- 可能原因: 入库和查询使用了不同 embedding 模型，升级模型后没有重建 collection，多个环境配置不一致。
- 排查步骤: 查看 collection embedding 配置；确认入库脚本和服务运行时使用同一个 embedding function；检查模型版本。
- 修复建议: embedding 模型变更时重建索引；collection metadata 写入 model_name 和 dimension；禁止混用向量维度。

### Chroma 持久化失败 sqlite disk I/O error
- 表现: 入库或查询初始化 Chroma 失败。
- 错误码/日志关键词: `sqlite disk I/O error`, `InternalError`, `chroma.sqlite3`, `PermissionError`, `database is locked`, `disk I/O error`
- 相关指标: persist directory 权限, 磁盘空间, 文件锁, 进程数。
- 可能原因: 持久化目录无权限，路径包含特殊字符导致底层兼容问题，磁盘空间不足，多进程同时写 Chroma。
- 排查步骤: 检查 `VECTOR_STORE_PATH`；确认目录可写；检查是否多个进程同时 ingest；查看磁盘空间；换到纯英文路径验证。
- 修复建议: 使用固定可写持久化目录；生产环境避免多进程同时写；入库任务串行化；必要时换独立向量数据库服务。

### Metadata 丢失导致证据不可追踪
- 表现: 答案有内容，但没有 source 或 topic，无法审计。
- 错误码/日志关键词: `metadata missing`, `source unknown`, `chunk_index missing`, `KeyError: source`, `evidence without source`
- 相关指标: metadata 完整率, source 字段为空比例。
- 可能原因: loader 未解析 metadata，chunk 时未继承标题信息，Chroma add 时 metadatas 为空。
- 排查步骤: 检查入库前 metadatas 列表；抽样查询结果 metadata；确认每个 chunk 都有 source、chunk_index、component、topic。
- 修复建议: 统一文档模板；Markdown-aware chunking 继承标题和 metadata；检索结果缺 source 时拒绝作为证据。

### Chunk 过大或过小影响召回
- 表现: 关键词能命中但答案上下文不足，或结果包含太多无关内容。
- 错误码/日志关键词: `chunk too large`, `chunk too small`, `context missing`, `token limit exceeded`, `topic mixed`
- 相关指标: chunk length, chunk count, average tokens, retrieval precision。
- 可能原因: 字符级切分破坏 Markdown 小节，一个 chunk 混入多个故障卡片，overlap 不合理。
- 排查步骤: 抽样查看 chunk 内容；确认一个 chunk 是否只包含一个故障场景；检查标题是否保留。
- 修复建议: 按 `###` 故障卡片切分；超长小节再按段落切；metadata 写入 section/topic；chunk_size 控制在 800-1200 字符。

### BM25 混合检索关键词召回未生效
- 表现: 用户输入错误码时没有优先返回包含该错误码的文档。
- 错误码/日志关键词: `BM25 no hit`, `keyword recall empty`, `error code not matched`, `1006`, `1205`, `NoSuchUpload`, `PRECONDITION_FAILED`
- 相关指标: BM25 hit count, vector hit count, merged top_k, reciprocal rank fusion score。
- 可能原因: 文档未显式写错误码，中文分词未保留英文错误码，错误码大小写归一化失败。
- 排查步骤: 用错误码直接查询 BM25；检查 tokenizer 输出；确认文档每个故障卡片都有错误码字段。
- 修复建议: 错误码原样写入 `错误码/日志关键词`；BM25 tokenizer 保留英文、数字、下划线；融合排序时提高错误码精确匹配权重。

## Runbook

### RAG 检索异常排查流程
1. 收集错误码: `CollectionNotFound`, `InvalidDimension`, `sqlite disk I/O error`, `metadata missing`。
2. 确认文档是否入库以及 collection count。
3. 打印 query、top_k、score、source、chunk content。
4. 对比 BM25 和 vector 的召回结果。
5. 检查 chunking 是否保留标题、错误码和 metadata。

## Prevention
- 每个故障卡片必须包含错误码/日志关键词。
- 入库时记录 chunk count 和 embedding model。
- 检索结果必须包含 source metadata。
- 使用 Markdown-aware chunking 和 BM25 + vector 混合检索。
