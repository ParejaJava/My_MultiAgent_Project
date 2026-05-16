---
title: 网关与高并发诊断知识库
category: traffic
service: Gateway
severity: critical
tags:
  - gateway
  - high-concurrency
  - nginx
  - timeout
  - rate-limit
  - circuit-breaker
  - thread-pool
  - connection-pool
error_codes:
  - 400
  - 401
  - 403
  - 404
  - 408
  - 413
  - 429
  - 499
  - 500
  - 502
  - 503
  - 504
  - ECONNRESET
  - upstream timed out
  - circuit breaker open
---

# 网关与高并发诊断知识库

## Metadata
- component: Gateway
- category: traffic
- tags: gateway, high concurrency, nginx, timeout, rate limit, circuit breaker, thread pool, connection pool
- common_errors: 400, 401, 403, 404, 408, 413, 429, 499, 500, 502, 503, 504, ECONNRESET, upstream timed out, circuit breaker open

## Overview
网关和高并发问题通常表现为 502、503、504、429、请求排队、下游超时、连接池耗尽和线程池打满。诊断时要按入口网关、应用服务、下游依赖、数据库/缓存/MQ 的顺序拆解瓶颈，并区分限流、熔断、超时、资源耗尽和发布变更。

## Symptoms

### 网关返回 502 Bad Gateway
- 表现: 客户端收到 502，后端可能无业务日志。
- 错误码/日志关键词: `502 Bad Gateway`, `upstream prematurely closed connection`, `connection reset by peer`, `no live upstreams`, `ECONNRESET`
- 相关指标: gateway 5xx, upstream unhealthy count, 后端实例重启次数。
- 可能原因: 后端实例崩溃，连接被重置，服务发现地址错误，容器重启，网关到后端网络异常。
- 排查步骤: 查看网关 access/error log；确认 upstream IP 和端口；检查后端实例健康状态；查看应用崩溃和重启日志。
- 修复建议: 修复异常实例并从负载均衡摘除；配置健康检查；发布时优雅下线；排查连接重置来源。

### 网关返回 503 Service Unavailable
- 表现: 服务不可用，流量高峰更明显。
- 错误码/日志关键词: `503 Service Unavailable`, `no healthy upstream`, `circuit breaker open`, `service unavailable`, `connection pool exhausted`
- 相关指标: upstream healthy count, 熔断打开次数, 连接池 active/pending, CPU。
- 可能原因: 下游全部不健康，熔断器打开，连接池耗尽，服务实例数不足。
- 排查步骤: 查看服务发现健康状态；检查熔断规则；检查连接池 pending；对比实例 CPU、内存和线程池。
- 修复建议: 恢复下游实例；临时扩容；调整熔断阈值；限制入口流量；优化连接池和线程池。

### 网关返回 504 Gateway Timeout
- 表现: 请求处理超过网关超时，客户端收到 504。
- 错误码/日志关键词: `504 Gateway Timeout`, `upstream timed out`, `Read timed out`, `response timeout`, `SocketTimeoutException`
- 相关指标: upstream response time, P95/P99 latency, slow request count。
- 可能原因: 后端接口慢，数据库慢 SQL，下游 RPC 超时，网关 timeout 小于业务处理时间。
- 排查步骤: 通过 trace id 串联网关和应用日志；查看慢接口和慢 SQL；确认网关、应用、RPC、DB 超时时间层级。
- 修复建议: 优化慢接口；设置合理超时层级；异步化长任务；对慢依赖降级；必要时调整网关 timeout。

### 请求被限流返回 429
- 表现: 高峰期部分请求被拒绝。
- 错误码/日志关键词: `429 Too Many Requests`, `rate limit exceeded`, `TooManyRequestsException`, `RequestRateLimiter`, `limit_req`
- 相关指标: QPS, rejected count, rate limiter tokens, user/IP 维度请求量。
- 可能原因: 限流阈值过低，突发流量超预期，单用户或单 IP 异常请求，预热不足。
- 排查步骤: 查看限流规则维度和阈值；统计被限流用户/IP/API；确认是否业务活动流量；检查是否有重试风暴。
- 修复建议: 按业务容量调整限流；区分用户/IP/API 维度；客户端指数退避；热点接口扩容和缓存。

### 客户端断开 499 或请求排队
- 表现: 网关记录 499，用户侧感觉请求失败或取消。
- 错误码/日志关键词: `499 Client Closed Request`, `client aborted`, `request canceled`, `queue timeout`, `pending acquire timeout`
- 相关指标: request queue length, pending connections, client timeout, upstream latency。
- 可能原因: 后端响应太慢，客户端超时小于服务端处理时间，连接池排队，移动端网络断开。
- 排查步骤: 比较客户端超时、网关超时、后端耗时；查看连接池 pending；检查接口 P99。
- 修复建议: 降低接口耗时；统一超时配置；连接池限流保护；长任务改异步。

### 请求体过大返回 413
- 表现: 上传文件或大请求失败。
- 错误码/日志关键词: `413 Payload Too Large`, `Request Entity Too Large`, `client_max_body_size`, `DataBufferLimitException`
- 相关指标: request body size, upload failure rate, gateway 413 count。
- 可能原因: Nginx body size 限制，Spring Gateway buffer 限制，单次上传过大。
- 排查步骤: 检查 Nginx `client_max_body_size`；检查应用上传限制；确认接口是否应走分片上传。
- 修复建议: 调整上传大小限制；大文件使用 MinIO 分片直传；限制单次请求体大小并返回明确提示。

### 高并发下线程池或连接池耗尽
- 表现: 接口大量超时，CPU 不一定很高，但请求排队严重。
- 错误码/日志关键词: `RejectedExecutionException`, `ThreadPoolTaskExecutor`, `HikariPool connection is not available`, `pending acquire timeout`, `BulkheadFullException`
- 相关指标: thread pool active/queue/rejected, DB pool active/pending, HTTP client pool pending。
- 可能原因: 线程池过小，慢依赖占满线程，连接池泄漏，外部接口超时过长，队列无界堆积。
- 排查步骤: 查看线程池和连接池监控；dump 线程栈；检查慢依赖；确认超时和重试次数。
- 修复建议: 设置有界队列和拒绝策略；缩短慢依赖超时；隔离核心/非核心线程池；连接池泄漏排查。

## Runbook

### 高并发网关异常排查流程
1. 收集入口错误码: `429`, `499`, `502`, `503`, `504`, `413`。
2. 判断是限流、网关超时、下游不可用、客户端断开还是请求体过大。
3. 通过 trace id 串联网关、应用、数据库、Redis、RabbitMQ 日志。
4. 检查线程池、连接池、队列长度和下游慢调用。
5. 临时处置优先级: 限流、扩容、降级、熔断、回滚。

## Prevention
- 统一超时层级: 客户端 > 网关 > 应用 > 下游依赖。
- 网关限流和熔断规则按接口容量配置。
- 所有线程池、连接池必须有监控和有界队列。
- 大文件上传走分片直传，不穿普通业务接口。
