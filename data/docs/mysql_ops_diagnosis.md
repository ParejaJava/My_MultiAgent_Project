---
title: MySQL 运维诊断知识库
category: database
service: MySQL
severity: critical
tags:
  - mysql
  - sql
  - slow-query
  - deadlock
  - lock-wait
  - connection-pool
  - replication
error_codes:
  - ER_LOCK_WAIT_TIMEOUT
  - ER_LOCK_DEADLOCK
  - ER_CON_COUNT_ERROR
  - ER_ACCESS_DENIED_ERROR
  - ER_DUP_ENTRY
  - ER_NO_REFERENCED_ROW_2
  - 1040
  - 1045
  - 1062
  - 1205
  - 1213
  - 2002
  - 2003
  - 2013
---

# MySQL 运维诊断知识库

## Metadata
- component: MySQL
- category: database
- tags: mysql, sql, slow query, deadlock, lock wait, connection pool, replication
- common_errors: ER_LOCK_WAIT_TIMEOUT, ER_LOCK_DEADLOCK, ER_CON_COUNT_ERROR, ER_ACCESS_DENIED_ERROR, ER_DUP_ENTRY, ER_NO_REFERENCED_ROW_2, 1040, 1045, 1062, 1205, 1213, 2002, 2003, 2013

## Overview
MySQL 是核心持久化存储。常见故障包括慢 SQL、锁等待、死锁、连接池耗尽、主从延迟、索引失效和磁盘 IO 飙高。诊断时要关注错误码、慢查询日志、连接数、事务状态、锁等待、执行计划和主从复制状态。

## Symptoms

### 慢 SQL 导致接口超时
- 表现: 接口响应慢，数据库 CPU 或 IO 升高。
- 错误码/日志关键词: `Query timeout`, `Communications link failure`, `2013 Lost connection to MySQL server during query`, `Slow query`, `Using filesort`, `Using temporary`
- 相关指标: QPS, TPS, slow_queries, CPU, IO utilization, buffer pool hit rate。
- 可能原因: 未命中索引，返回数据量过大，排序和临时表过多，统计信息不准，SQL 写法导致全表扫描。
- 排查步骤: 查看慢查询日志；执行 `EXPLAIN`；检查 rows、type、key、Extra；确认 where/order by/group by 字段是否有合适索引。
- 修复建议: 添加或调整索引；分页限制；避免 select *；优化排序字段；必要时拆分复杂 SQL。

### 锁等待超时 Lock wait timeout exceeded
- 表现: 写操作卡住后失败，业务事务回滚。
- 错误码/日志关键词: `1205`, `ER_LOCK_WAIT_TIMEOUT`, `Lock wait timeout exceeded; try restarting transaction`, `innodb_lock_wait_timeout`
- 相关指标: lock waits, trx running time, row lock time, active transactions。
- 可能原因: 长事务未提交，热点行更新，事务范围过大，索引缺失导致锁范围扩大。
- 排查步骤: 查询 `information_schema.innodb_trx`；查看锁等待关系；检查长事务 SQL；确认 update/delete 条件是否命中索引。
- 修复建议: 缩短事务；热点数据拆分；补充索引；失败后安全重试；避免事务中调用慢外部接口。

### MySQL 死锁 Deadlock found
- 表现: 并发写入时部分请求失败，重试后可能成功。
- 错误码/日志关键词: `1213`, `ER_LOCK_DEADLOCK`, `Deadlock found when trying to get lock`, `SHOW ENGINE INNODB STATUS`
- 相关指标: deadlocks, transaction rollback count, 并发写 QPS。
- 可能原因: 多事务更新顺序不一致，批量更新排序不稳定，唯一索引冲突，外键级联锁。
- 排查步骤: 执行 `SHOW ENGINE INNODB STATUS` 查看 latest detected deadlock；定位两边事务 SQL；检查更新顺序和索引。
- 修复建议: 统一资源访问顺序；批量更新按主键排序；缩短事务；对死锁错误做幂等重试。

### 连接数过多或连接池耗尽
- 表现: 应用无法获取数据库连接，请求排队或失败。
- 错误码/日志关键词: `1040 Too many connections`, `ER_CON_COUNT_ERROR`, `HikariPool-1 - Connection is not available`, `Connection timed out`, `2003 Can't connect to MySQL server`
- 相关指标: MySQL `Threads_connected`, `max_connections`, 连接池 active/idle/pending。
- 可能原因: 连接池过小，慢 SQL 占用连接，连接泄漏，突发流量，MySQL max_connections 太低。
- 排查步骤: 查看连接池监控；查询 `SHOW PROCESSLIST`；按 host/user 统计连接；检查是否有 Sleep 连接堆积。
- 修复建议: 优化慢 SQL；修复连接泄漏；合理设置连接池和 max_connections；增加接口限流。

### 主从复制延迟
- 表现: 写入后立刻读取查不到，读写分离场景数据不一致。
- 错误码/日志关键词: `Seconds_Behind_Master`, `Replica_IO_Running: No`, `Replica_SQL_Running: No`, `Duplicate entry`, `Could not execute Write_rows event`
- 相关指标: replication lag, relay log size, replica SQL thread 状态。
- 可能原因: 从库执行慢，主库大事务，网络延迟，复制线程报错停止，表缺少主键。
- 排查步骤: 执行 `SHOW REPLICA STATUS`；查看 SQL thread error；检查大事务和慢 SQL；确认从库 IO/CPU。
- 修复建议: 读写一致性场景走主库；拆分大事务；修复复制错误；提升从库资源。

### 唯一键冲突或数据约束失败
- 表现: 写入失败，业务提示重复提交或外键错误。
- 错误码/日志关键词: `1062 Duplicate entry`, `ER_DUP_ENTRY`, `1452 Cannot add or update a child row`, `ER_NO_REFERENCED_ROW_2`, `DataIntegrityViolationException`
- 相关指标: 写入失败率, 重试次数, 唯一键冲突数。
- 可能原因: 重复请求未幂等，唯一索引设计不合理，外键引用数据不存在，消息重复消费。
- 排查步骤: 查看失败 SQL 和唯一索引字段；确认请求 idempotency key；检查 MQ 消息是否重复投递。
- 修复建议: 增加幂等表或唯一业务键；重复写使用 upsert；消费端幂等处理；外键数据先校验。

## Runbook

### MySQL 接口慢和错误排查流程
1. 收集错误码: `1205`, `1213`, `1040`, `1062`, `2013`, `2003`。
2. 查看慢查询日志和 `SHOW PROCESSLIST`。
3. 检查锁等待、死锁和长事务。
4. 检查连接池 active/pending 和 MySQL max_connections。
5. 检查主从延迟和复制线程状态。

## Prevention
- 所有核心 SQL 需要执行计划评审。
- 事务内不调用外部慢接口。
- 对 `1205` 和 `1213` 做幂等重试。
- 监控慢查询、连接数、锁等待、死锁、复制延迟和磁盘 IO。
