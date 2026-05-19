# 多 Agent 运维诊断 Copilot V0 版本说明

## 1. 项目定位

本项目当前 V0 是一个 Python 运维故障诊断 Copilot 原型系统。

它不是一个单文件 demo，而是一个可持续演进的多模块系统，核心能力包括：

- FastAPI HTTP 服务入口
- LangGraph 多 Agent 编排
- Intent 结构化解析
- RAG 知识库检索
- Dense Vector + BM25 Hybrid Search
- RRF 融合
- 可选 reranker 抽象
- Kimi/OpenAI-compatible LLM 生成诊断答案
- 离线 retrieval-only 评测闭环

当前系统的重点是把“故障问题 -> 结构化理解 -> 检索证据 -> 生成诊断答案 -> 离线评测”的主链路搭起来，并且让后续每个能力都可以通过配置独立替换。

## 2. 当前目录结构

```text
app/
  main.py                  FastAPI 入口
  agents/                  诊断流程中的窄职责 Agent
  graph/                   LangGraph 状态和 workflow
  rag/                     RAG 检索、融合、重排、答案生成
  llm/                     LLM provider 抽象
  schemas/                 Pydantic schema
  tools/                   确定性工具

configs/rag/               RAG 实验配置
data/docs/                 运维故障知识库文档
eval/                      离线评测集和评测结果
scripts/                   入库、评测、对比、命令行问答脚本
tests/                     单元测试和流程测试
```

## 3. HTTP API

FastAPI 入口位于：

```text
app/main.py
```

当前提供：

```text
GET  /health
POST /diagnose
```

`POST /diagnose` 会调用 LangGraph workflow，执行当前诊断流程。

## 4. LangGraph 多 Agent 编排

workflow 位于：

```text
app/graph/workflow.py
```

状态结构位于：

```text
app/graph/state.py
```

当前状态字段包括：

```text
user_question
log_text
intent
retrieved_docs
log_findings
root_causes
solution
final_report
next_agent
last_agent
workflow_status
```

当前图已经从顺序流程升级为 Supervisor 动态路由模式：

```text
supervisor
  -> intent_agent
  -> retrieval_agent
  -> log_analysis_agent
  -> diagnosis_agent
  -> solution_agent
```

特殊路由：

- 没有日志时跳过 `log_analysis_agent`
- 检索为空时进入 `fallback_answer`
- 信息不足时进入 `clarification_needed`

## 5. Intent Agent

Intent Agent 位于：

```text
app/agents/intent.py
app/schemas/intent.py
```

它将用户问题解析为结构化字段：

```text
system
symptom
error_codes
time_range
severity
```

当前主要基于规则解析，后续可以替换为 LLM 结构化抽取。

## 6. 知识库文档

当前知识库位于：

```text
data/docs/
```

已覆盖主题：

```text
minio_multipart_resume.md
redis_ops_diagnosis.md
rabbitmq_ops_diagnosis.md
mysql_ops_diagnosis.md
websocket_ops_diagnosis.md
rag_ops_diagnosis.md
gateway_high_concurrency.md
```

每篇文档包含 YAML frontmatter：

```yaml
---
title:
category:
service:
severity:
tags:
error_codes:
---
```

正文采用故障卡片结构：

```markdown
### 具体故障场景
- 表现:
- 错误码/日志关键词:
- 相关指标:
- 可能原因:
- 排查步骤:
- 修复建议:
```

这个格式是为了后续 Markdown-aware chunking、BM25 关键词召回、metadata filter 和可审计引用做准备。

## 7. RAG 检索系统

RAG 模块位于：

```text
app/rag/
```

核心模块：

```text
loader.py             读取 markdown 文档
splitter.py           文本 chunk
embeddings.py         embedding provider 抽象
vector_store.py       Chroma 入库和 dense 查询
retriever.py          dense retriever 对外接口
bm25_store.py         本地 BM25 检索
fusion.py             RRF 融合
hybrid_retriever.py   Dense + BM25 Hybrid Search
reranker.py           reranker provider 抽象
answer_generator.py   基于检索上下文生成答案
config.py             RAG YAML 配置读取
```

### 7.1 Dense Vector Retrieval

当前 dense 检索使用 Chroma。

入口：

```text
app/rag/retriever.py
```

对外函数：

```python
retrieve_documents(query, top_k=3, config_path=None)
```

注意：该接口没有被删除，保持兼容。

### 7.2 Embedding Provider

embedding 抽象位于：

```text
app/rag/embeddings.py
```

支持：

```text
hash
openai
bge_local
```

当前默认 baseline 是：

```yaml
embedding:
  provider: hash
  dimensions: 64
```

说明：

- `hash` 是本地确定性 embedding，不需要网络和 API Key
- `openai` 使用环境变量 `OPENAI_API_KEY`
- `bge_local` 使用 `FlagEmbedding.FlagModel`

不同 embedding provider 必须使用不同 Chroma collection，避免不同向量空间混用。

### 7.3 BM25 + Dense Hybrid Search

Hybrid 检索入口：

```text
app/rag/hybrid_retriever.py
```

流程：

```text
dense retriever 从 Chroma 取 retrieve_top_n
BM25 retriever 从本地 markdown chunk 取 retrieve_top_n
RRF 融合
reranker 重排
截断 rerank_top_k
```

BM25 模块：

```text
app/rag/bm25_store.py
```

RRF 模块：

```text
app/rag/fusion.py
```

RRF 默认参数：

```yaml
ranking:
  rrf_k: 60
```

Hybrid 返回结果仍然使用 `RetrievedDocument`，metadata 中保留：

```text
source
chunk_index
retrieval_method
dense_rank
bm25_rank
rrf_score
original_rank
final_rank
rerank_score
```

### 7.4 Reranker

reranker 抽象位于：

```text
app/rag/reranker.py
```

支持：

```text
none
bge
```

当前默认使用：

```yaml
reranker:
  provider: none
```

BGE reranker 配置示例：

```yaml
reranker:
  provider: bge
  model: D:/AgentData/Models/bge-reranker-base
  implementation: flag_embedding
  use_fp16: true
  devices:
    - cuda:1
  query_max_length: 256
  passage_max_length: 512
  batch_size: 16
```

BGE reranker 使用 `FlagEmbedding.FlagReranker` 对 query-document pair 打分：

```text
input:  [query, document.content]
output: relevance score
```

当前阶段已经完成真实 reranker 接入，运行前需要安装 FlagEmbedding。

## 8. LLM 生成能力

LLM provider 位于：

```text
app/llm/providers.py
```

支持：

```text
mock
kimi
```

### 8.1 Mock Provider

用于测试和离线开发：

```yaml
llm:
  provider: mock
```

不需要网络，不需要 API Key。

### 8.2 Kimi Provider

Kimi API 兼容 OpenAI API 格式，因此代码使用 `openai>=1.0` SDK。

配置示例：

```yaml
llm:
  provider: kimi
  model: kimi-k2.6
  base_url: https://api.moonshot.cn/v1
  api_key_env: MOONSHOT_API_KEY
  temperature: 0.2
  max_tokens: 1200
  timeout: 60
```

API Key 从环境变量读取：

```powershell
$env:MOONSHOT_API_KEY="你的 key"
```

代码不会写死 key。

### 8.3 Answer Generator

答案生成模块：

```text
app/rag/answer_generator.py
```

输入：

```text
user question
retrieved documents
llm config
```

输出：

```text
answer
cited_sources
used_contexts
```

prompt 约束：

- 只能基于检索上下文回答
- 不得编造上下文中没有的故障原因、命令或解决步骤
- 如果上下文不足，必须说明“根据当前知识库无法确定”
- 答案包含：可能原因、排查步骤、解决方案
- 必须保留 source 引用

引用格式：

```text
[source: <source>#chunk_<chunk_index>]
[source: <source>]
```

## 9. 命令行脚本

### 9.1 文档入库

```powershell
python scripts/ingest_docs.py --config configs/rag/baseline_hash.yaml
```

切换 embedding provider 后，必须使用同一份 config 重新入库：

```powershell
python scripts/ingest_docs.py --config configs/rag/openai_embedding.yaml
python scripts/ingest_docs.py --config configs/rag/bge_local.yaml
```

### 9.2 Retrieval-only 离线评测

```powershell
python scripts/evaluate_rag.py --config configs/rag/hybrid_hash_rrf.yaml --top-k 5
```

该脚本只评估 retrieval，不调用 LLM。

输出：

```text
eval/results/rag_eval.json
eval/results/rag_eval.md
```

### 9.3 多次实验对比

```powershell
python scripts/compare_rag_runs.py `
  eval/results/rag_eval.json `
  eval/results/hybrid_hash_rrf/rag_eval.json `
  --output-file eval/results/rag_compare.md
```

对比指标：

```text
Recall@k
Precision@k
Hit Rate@k
MRR
NDCG@k
```

### 9.4 命令行问答

使用 mock 生成：

```powershell
python scripts/ask_rag.py `
  --config configs/rag/hybrid_hash_rrf.yaml `
  --question "Redis READONLY 怎么处理？" `
  --top-k 3
```

使用 Kimi 生成：

```powershell
$env:MOONSHOT_API_KEY="你的 key"

python scripts/ask_rag.py `
  --config configs/rag/kimi_generation.yaml `
  --question "Redis READONLY 怎么处理？" `
  --top-k 3
```

## 10. 当前配置文件

```text
configs/rag/baseline_hash.yaml
configs/rag/hybrid_hash_rrf.yaml
configs/rag/hybrid_rrf_rerank.yaml
configs/rag/openai_embedding.yaml
configs/rag/bge_local.yaml
configs/rag/kimi_generation.yaml
```

当前已经具备配置化实验能力：

```text
embedding provider
collection_name
chunk_size
overlap
retriever
retrieve_top_n
rerank_top_k
rrf_k
reranker provider/model
LLM provider/model/base_url
```

## 11. 离线评测集

评测集：

```text
eval/questions.jsonl
```

每条样本包含：

```text
id
question
category
difficulty
expected_sources
expected_keywords
reference_answer
```

当前覆盖：

```text
object-storage
cache
message-queue
database
realtime
retrieval
traffic
```

每类至少包含口语化问题，用于后续 query rewrite 测试。

## 12. 当前测试覆盖

测试目录：

```text
tests/
```

已覆盖：

- health endpoint
- diagnose endpoint
- intent extraction
- retrieval
- workflow supervisor routing
- embedding provider
- BM25
- RRF
- hybrid retriever metadata
- reranker abstraction
- answer generation
- LLM provider error handling
- evaluation metric calculation

运行：

```powershell
python -m pytest
```

## 13. 当前 V0 能力边界

已经具备：

- 可运行 FastAPI 服务
- LangGraph 多 Agent 编排
- 中文故障知识库
- Chroma dense retrieval
- BM25 keyword retrieval
- Hybrid Search
- RRF 融合
- reranker 抽象
- Kimi LLM provider 抽象
- 基于上下文生成诊断答案
- retrieval-only 离线评测闭环
- 多实验结果对比

暂未实现：

- Markdown-aware chunking
- query rewrite
- metadata filter
- 真正生产级 embedding 模型默认启用
- BGE reranker 本地实跑验证
- RAGAS
- LLM 答案质量自动评测
- Web UI
- 真实 Agent 工具调用闭环

## 14. 下一步建议

是的，下一步可以开始调整配置中的 embedding 模型、reranker 模型和 LLM API。

建议顺序如下：

### 第一步：先调 embedding

目标是让 dense retrieval 真正可用。

可选配置：

```text
configs/rag/openai_embedding.yaml
configs/rag/bge_local.yaml
```

切换后必须重新入库：

```powershell
python scripts/ingest_docs.py --config configs/rag/openai_embedding.yaml
python scripts/evaluate_rag.py --config configs/rag/openai_embedding.yaml --top-k 5
```

或：

```powershell
python scripts/ingest_docs.py --config configs/rag/bge_local.yaml
python scripts/evaluate_rag.py --config configs/rag/bge_local.yaml --top-k 5
```

### 第二步：再调 hybrid 参数

重点参数：

```yaml
ranking:
  retrieve_top_n: 10
  rerank_top_k: 3
  rrf_k: 60
```

建议实验：

```text
retrieve_top_n: 10 / 20 / 30
rerank_top_k: 3 / 5
rrf_k: 30 / 60 / 100
```

每次都跑：

```powershell
python scripts/evaluate_rag.py --config <config> --top-k 5
```

### 第三步：接入 BGE reranker

配置：

```text
configs/rag/hybrid_rrf_rerank.yaml
```

需要先安装 FlagEmbedding。

目标是观察：

```text
MRR
NDCG@k
```

是否提升。

### 第四步：接入 Kimi 生成

配置：

```text
configs/rag/kimi_generation.yaml
```

运行：

```powershell
$env:MOONSHOT_API_KEY="你的 key"

python scripts/ask_rag.py `
  --config configs/rag/kimi_generation.yaml `
  --question "Redis READONLY 怎么处理？" `
  --top-k 3
```

### 第五步：固定实验闭环

后续每次优化 RAG 都应执行：

```powershell
python scripts/evaluate_rag.py --top-k 5
```

如果使用特定配置：

```powershell
python scripts/evaluate_rag.py --config <config_path> --top-k 5
```

然后用 compare 脚本对比：

```powershell
python scripts/compare_rag_runs.py <old_json> <new_json> --output-file eval/results/rag_compare.md
```

## 15. V0 结论

当前项目已经从“基础骨架”进入“可实验 RAG Copilot”阶段。

最重要的下一步不是继续堆新功能，而是开始做配置化实验：

1. 换真实 embedding 模型
2. 重新 ingest
3. 跑 retrieval-only eval
4. 比较指标
5. 再接 reranker
6. 最后接 Kimi 生成答案

这样每一步都有指标闭环，系统会比较稳地向 V1 演进。
