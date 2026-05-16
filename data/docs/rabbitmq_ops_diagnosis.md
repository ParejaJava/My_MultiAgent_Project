---
title: RabbitMQ 运维诊断知识库
category: message-queue
service: RabbitMQ
severity: high
tags:
  - rabbitmq
  - mq
  - queue
  - exchange
  - ack
  - dead-letter
  - consumer
  - prefetch
error_codes:
  - AMQP_CONNECTION_FORCED
  - PRECONDITION_FAILED
  - NOT_FOUND
  - ACCESS_REFUSED
  - RESOURCE_LOCKED
  - CHANNEL_ERROR
  - CONNECTION_FORCED
  - 320
  - 403
  - 404
  - 405
  - 406
  - 541
---

# RabbitMQ 运维诊断知识库

## Metadata
- component: RabbitMQ
- category: message-queue
- tags: rabbitmq, mq, queue, exchange, ack, dead letter, consumer, prefetch
- common_errors: AMQP_CONNECTION_FORCED, PRECONDITION_FAILED, NOT_FOUND, ACCESS_REFUSED, RESOURCE_LOCKED, CHANNEL_ERROR, CONNECTION_FORCED, 320, 404, 405, 406, 403, 541

## Overview
RabbitMQ 常用于异步解耦、削峰填谷和事件驱动。常见故障包括消息堆积、消费者掉线、ack 异常、死信增长、exchange/queue 绑定错误、磁盘水位和内存水位告警。诊断时要关注 queue depth、consumer count、ack rate、publish rate、redeliver rate 和 broker alarms。

## Symptoms

### 消息堆积 messages_ready 持续升高
- 表现: 队列积压越来越多，业务处理延迟增加。
- 错误码/日志关键词: `messages_ready`, `messages_unacknowledged`, `consumer_timeout`, `basic.deliver`, `consumer count 0`, `queue depth high`
- 相关指标: publish rate, deliver rate, ack rate, consumer count, messages_ready。
- 可能原因: 消费者实例不足，消费逻辑变慢，下游数据库或接口超时，prefetch 太大，消费者异常退出。
- 排查步骤: 查看 RabbitMQ management 队列详情；确认 consumer count；对比 publish rate 和 ack rate；检查消费者应用日志和下游依赖。
- 修复建议: 扩容消费者；优化消费逻辑；降低单条消息处理耗时；对下游增加超时和降级；调整 prefetch。

### 消息未确认 messages_unacknowledged 过高
- 表现: 队列 ready 不高但 unacked 很高，消费者像是卡住。
- 错误码/日志关键词: `messages_unacknowledged`, `basic.ack`, `basic.nack`, `PRECONDITION_FAILED unknown delivery tag`, `consumer_timeout`
- 相关指标: unacked 数量, consumer ack rate, 消费耗时, prefetch count。
- 可能原因: 消费者处理后未 ack，业务线程阻塞，prefetch 设置过大，ack 使用了错误 channel，消费者崩溃前未释放。
- 排查步骤: 检查消费代码 ack/nack/finally；查看线程池是否打满；检查 prefetch；确认一个 delivery tag 只在原 channel ack。
- 修复建议: 消费成功后及时 ack；异常时 nack/requeue 或投递死信；降低 prefetch；消费逻辑幂等化。

### 队列或交换机不存在导致投递失败
- 表现: 发布消息失败，或者消息发送成功但没有消费者收到。
- 错误码/日志关键词: `404 NOT_FOUND`, `no queue`, `no exchange`, `NO_ROUTE`, `mandatory returned`, `basic.return`, `reply-code=312`
- 相关指标: publish error, unroutable messages, exchange binding 数量。
- 可能原因: queue/exchange 未声明，vhost 错误，routing key 不匹配，绑定关系丢失，生产者和消费者环境配置不一致。
- 排查步骤: 检查 vhost、exchange、queue、routing key；查看 bindings；确认生产者 mandatory return callback；对比配置中心。
- 修复建议: 启动时自动声明拓扑；固定命名规范；发送端开启 mandatory；未路由消息进入告警或备用 exchange。

### 声明参数不一致 PRECONDITION_FAILED
- 表现: 应用启动失败，RabbitMQ channel 被关闭。
- 错误码/日志关键词: `406 PRECONDITION_FAILED`, `inequivalent arg`, `received 'true' but current is 'false'`, `x-dead-letter-exchange`, `durable`
- 相关指标: channel close count, 应用启动失败次数。
- 可能原因: 已存在 queue/exchange 的 durable、autoDelete、arguments 与新代码声明不一致。
- 排查步骤: 查看 RabbitMQ 中队列实际参数；对比代码声明参数；检查死信 exchange、TTL、max length 等 arguments。
- 修复建议: 不直接修改已有队列不可变参数；新建队列迁移；统一队列声明配置；基础设施脚本托管拓扑。

### 死信队列持续增长
- 表现: DLQ 消息越来越多，业务数据处理失败。
- 错误码/日志关键词: `x-death`, `dead-letter-exchange`, `basic.reject`, `basic.nack`, `requeue=false`, `TTL expired`, `maxlen exceeded`
- 相关指标: dead letter queue depth, redelivered count, 消费失败率。
- 可能原因: 消费代码抛异常，消息格式不兼容，业务校验失败，重试次数耗尽，队列 TTL 过期。
- 排查步骤: 抽样查看 DLQ 消息 headers 的 `x-death`；检查失败堆栈；确认消息 schema 版本；统计失败原因。
- 修复建议: 增加失败分类；可恢复错误延迟重试；不可恢复错误入 DLQ 并告警；消费者兼容多版本消息格式。

### RabbitMQ 磁盘或内存水位报警
- 表现: 生产者发送变慢或被阻塞，队列停止接收消息。
- 错误码/日志关键词: `disk_free_limit`, `memory alarm`, `resource alarm`, `connection.blocked`, `blocked connection`, `vm_memory_high_watermark`
- 相关指标: disk free, memory used, file descriptors, queue depth。
- 可能原因: 消息堆积导致磁盘占用高，内存水位过高，持久化消息过多，消费者不可用。
- 排查步骤: 查看 Overview alarms；检查最大队列；清理无用队列；确认消费者恢复；检查磁盘剩余空间。
- 修复建议: 扩容磁盘；恢复消费者；设置队列 TTL 和 max length；开启惰性队列或升级集群容量。

## Runbook

### RabbitMQ 消息堆积排查流程
1. 收集错误码: `404 NOT_FOUND`, `406 PRECONDITION_FAILED`, `connection.blocked`, `x-death`。
2. 查看 queue 的 ready、unacked、consumer count。
3. 对比 publish rate 与 ack rate。
4. 检查消费者日志、线程池和下游依赖。
5. 检查 broker memory/disk alarm。

## Prevention
- 所有队列、交换机和绑定关系通过 IaC 或启动脚本统一声明。
- 消费者必须保证 ack/nack 逻辑清晰，业务处理幂等。
- 配置 DLQ、重试队列和告警。
- 监控 `messages_ready`, `messages_unacknowledged`, `consumer_count`, `ack_rate`, `disk_free_limit`, `memory alarm`。
