---
title: Redis 运维诊断知识库
category: cache
service: Redis
severity: high
tags:
  - redis
  - cache
  - timeout
  - latency
  - memory
  - lock
  - hot-key
  - big-key
error_codes:
  - LOADING
  - MISCONF
  - READONLY
  - NOAUTH
  - WRONGPASS
  - BUSY
  - OOM command not allowed
  - max number of clients reached
  - MOVED
  - ASK
  - 10054
  - 111
  - 6379
---

# Redis 运维诊断知识库

## Metadata
- component: Redis
- category: cache
- tags: redis, cache, timeout, latency, memory, lock, hot key, big key
- common_errors: LOADING, MISCONF, READONLY, NOAUTH, WRONGPASS, BUSY, OOM command not allowed, max number of clients reached, MOVED, ASK, 10054, 111, 6379

## Overview
Redis 常用于缓存、分布式锁、会话和限流。Redis 故障通常表现为接口变慢、连接超时、缓存命中率下降、锁失效、内存打满或主从切换异常。诊断时要结合应用日志、Redis 慢查询、连接数、内存、淘汰键、命中率和主从状态。

## Symptoms

### Redis 连接失败或连接超时
- 表现: 应用请求 Redis 超时，接口响应变慢或大量失败。
- 错误码/日志关键词: `RedisConnectionException`, `JedisConnectionException`, `LettuceConnectionException`, `Connection refused`, `Connection timed out`, `ECONNRESET`, `10054`, `111`, `max number of clients reached`
- 相关指标: `connected_clients`, `blocked_clients`, `tcp_backlog`, 应用连接池 active/idle/waiting。
- 可能原因: Redis 连接数达到上限，网络不通，连接池配置过小，客户端连接泄漏，Redis 进程重启。
- 排查步骤: 执行 `INFO clients` 查看连接数；检查应用连接池配置；检查 Redis `maxclients`；检查安全组、防火墙和 DNS；查看 Redis 重启日志。
- 修复建议: 调整连接池最大连接数和超时；修复连接泄漏；增加 Redis `maxclients`；对连接失败加入降级和重试。

### Redis 慢查询或命令延迟升高
- 表现: 缓存访问偶发慢，接口 P95/P99 延迟升高。
- 错误码/日志关键词: `Redis command timed out`, `Command timed out`, `Read timed out`, `BUSY Redis is busy running a script`, `SLOWLOG`, `Lua script timed out`
- 相关指标: `slowlog get`, `instantaneous_ops_per_sec`, `used_cpu_sys`, `latency latest`, `blocked_clients`。
- 可能原因: 大 key 操作，Lua 脚本阻塞，`KEYS`/`HGETALL`/`SMEMBERS` 大集合命令，持久化 fork 导致抖动。
- 排查步骤: 查看 `SLOWLOG GET 20`；检查是否有 `KEYS *`；扫描大 key；查看 latency doctor；检查 RDB/AOF rewrite 时间。
- 修复建议: 禁止线上使用阻塞命令；大 key 拆分；Lua 脚本限时和拆分；使用 scan 代替 keys；优化持久化策略。

### Redis 内存不足或 OOM
- 表现: 写入失败，缓存大量淘汰，命中率下降。
- 错误码/日志关键词: `OOM command not allowed when used memory > maxmemory`, `evicted_keys`, `used_memory_peak`, `maxmemory`, `MISCONF`
- 相关指标: `used_memory`, `used_memory_rss`, `mem_fragmentation_ratio`, `evicted_keys`, `expired_keys`。
- 可能原因: 热数据增长，未设置 TTL，大 key 过多，淘汰策略不合适，内存碎片高。
- 排查步骤: 执行 `INFO memory`；抽样扫描大 key；检查 key TTL 分布；确认 `maxmemory-policy`；观察 `evicted_keys` 是否增长。
- 修复建议: 设置合理 TTL；清理无用 key；拆分大 key；调整淘汰策略为 `allkeys-lru` 或业务适配策略；扩容 Redis。

### Redis 持久化失败 MISCONF
- 表现: Redis 读正常但写入失败。
- 错误码/日志关键词: `MISCONF Redis is configured to save RDB snapshots`, `stop-writes-on-bgsave-error`, `Background saving error`, `Can't save in background`
- 相关指标: `rdb_last_bgsave_status`, `rdb_last_bgsave_time_sec`, 磁盘空间, Redis 日志。
- 可能原因: 磁盘满，目录权限错误，RDB fork 失败，宿主机内存不足。
- 排查步骤: 查看 Redis 日志；检查磁盘空间和 Redis data 目录权限；执行 `INFO persistence`；确认是否触发 bgsave 失败。
- 修复建议: 释放磁盘空间；修复目录权限；临时关闭 `stop-writes-on-bgsave-error` 需谨慎；优化持久化配置。

### Redis 主从切换后写入 READONLY
- 表现: 应用写 Redis 失败，读请求可能正常。
- 错误码/日志关键词: `READONLY You can't write against a read only replica`, `MOVED`, `ASK`, `CLUSTERDOWN`, `master_link_status:down`
- 相关指标: `role`, `master_link_status`, Sentinel failover 日志, cluster slots 状态。
- 可能原因: 客户端仍连接旧主节点，Sentinel 或 Cluster 拓扑未刷新，代理未更新路由。
- 排查步骤: 执行 `INFO replication`；检查客户端是否支持拓扑刷新；检查 Sentinel failover 记录；确认写请求是否打到 replica。
- 修复建议: 启用 Lettuce/Jedis 拓扑自动刷新；修复 Redis 代理路由；在故障切换后重建连接池。

### 缓存雪崩、击穿或穿透
- 表现: Redis 命中率下降，数据库压力飙升，接口大量超时。
- 错误码/日志关键词: `cache miss`, `DB timeout`, `Too many connections`, `Lock wait timeout exceeded`, `keyspace_misses`, `nil cache`, `hot key`
- 相关指标: `keyspace_hits`, `keyspace_misses`, DB QPS, Redis QPS, 热 key 访问量。
- 可能原因: 大量 key 同时过期，热点 key 失效，无效参数绕过缓存，分布式锁未保护回源。
- 排查步骤: 查看命中率趋势；检查 key TTL 是否集中；识别热点 key；统计空结果请求参数。
- 修复建议: TTL 加随机抖动；热点 key 永不过期或异步刷新；空值缓存；布隆过滤器；回源加互斥锁。

## Runbook

### Redis 延迟升高排查流程
1. 查看应用错误码: `Redis command timed out`, `Connection timed out`, `BUSY`, `OOM`。
2. 查看 `INFO clients`, `INFO memory`, `INFO stats`, `INFO persistence`。
3. 检查 `SLOWLOG GET` 和大 key。
4. 判断是连接问题、命令阻塞、内存问题还是主从切换。
5. 对热点缓存和回源链路做限流、降级和互斥保护。

## Prevention
- 禁止生产使用 `KEYS`, 大集合全量读取和长 Lua。
- 所有缓存 key 设置合理 TTL 和随机抖动。
- 监控 `connected_clients`, `used_memory`, `evicted_keys`, `keyspace_misses`, `slowlog`。
- Redis 客户端启用合理超时、连接池和拓扑刷新。
