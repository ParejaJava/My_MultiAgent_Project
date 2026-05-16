---
title: WebSocket 运维诊断知识库
category: realtime
service: WebSocket
severity: medium
tags:
  - websocket
  - realtime
  - heartbeat
  - gateway
  - connection
  - session
  - broadcast
error_codes:
  - 1000
  - 1001
  - 1002
  - 1006
  - 1008
  - 1011
  - 400
  - 401
  - 403
  - 404
  - 426
  - 502
  - 503
  - 504
  - ECONNRESET
  - Broken pipe
---

# WebSocket 运维诊断知识库

## Metadata
- component: WebSocket
- category: realtime
- tags: websocket, realtime, heartbeat, gateway, connection, session, broadcast
- common_errors: 1000, 1001, 1002, 1006, 1008, 1011, 400, 401, 403, 404, 426, 502, 503, 504, ECONNRESET, Broken pipe

## Overview
WebSocket 常用于实时通知、在线状态、协作和消息推送。故障通常表现为连接失败、频繁断开、心跳超时、消息丢失、广播不一致或网关超时。诊断时要同时检查客户端 close code、网关配置、服务端连接数、心跳机制、鉴权 token 和多实例会话路由。

## Symptoms

### WebSocket 握手失败 401/403/426
- 表现: 客户端无法建立 WebSocket 连接。
- 错误码/日志关键词: `401 Unauthorized`, `403 Forbidden`, `426 Upgrade Required`, `Handshake failed`, `Invalid token`, `Missing Sec-WebSocket-Key`, `Upgrade header missing`
- 相关指标: 握手失败率, 网关 4xx, 鉴权失败日志。
- 可能原因: token 过期，鉴权参数缺失，网关没有转发 `Upgrade` 和 `Connection` header，路径路由错误。
- 排查步骤: 抓包检查握手请求头；确认 URL、token、子协议；检查 Nginx 或 Gateway 是否支持 websocket upgrade；查看后端鉴权日志。
- 修复建议: 网关配置 `proxy_set_header Upgrade $http_upgrade`；token 刷新机制；握手失败返回明确错误；统一连接 URL 配置。

### 连接频繁断开 close code 1006
- 表现: 连接建立后短时间内断开，客户端收到 abnormal closure。
- 错误码/日志关键词: `1006 Abnormal Closure`, `ECONNRESET`, `Broken pipe`, `Connection reset by peer`, `client disconnected`, `idle timeout`
- 相关指标: connection close rate, active connections, 网关 idle timeout。
- 可能原因: 网关 idle timeout 小于心跳间隔，客户端网络切换，服务端实例重启，发送大消息阻塞。
- 排查步骤: 对比心跳间隔和网关超时；查看服务端重启记录；检查断开时间是否固定；检查客户端网络事件。
- 修复建议: 心跳间隔设置为网关 idle timeout 的 1/2 或 1/3；断线自动重连；服务端优雅下线；限制单条消息大小。

### 心跳超时导致误断开
- 表现: 实际网络正常，但服务端认为客户端离线。
- 错误码/日志关键词: `heartbeat timeout`, `ping timeout`, `pong timeout`, `1001 Going Away`, `session expired`, `read idle`
- 相关指标: heartbeat miss count, event loop delay, GC pause, 消息发送队列长度。
- 可能原因: 心跳线程被阻塞，客户端页面后台限频，服务端事件循环阻塞，网络抖动。
- 排查步骤: 查看服务端 event loop/线程池；检查 GC 日志；对比客户端 ping/pong 时间；检查是否有大消息发送。
- 修复建议: 心跳容忍连续多次失败；后台页面延长心跳窗口；避免阻塞 IO 线程；大消息拆分。

### 多实例部署消息丢失或只推送到部分用户
- 表现: 单实例正常，多实例后广播或点对点消息不稳定。
- 错误码/日志关键词: `session not found`, `user channel missing`, `broadcast miss`, `Redis pubsub disconnected`, `RabbitMQ consumer cancelled`
- 相关指标: 每实例连接数, pub/sub 延迟, 广播成功率。
- 可能原因: 会话只存在本机内存，负载均衡无粘性会话，跨实例广播通道异常，用户连接映射未共享。
- 排查步骤: 查询用户连接在哪个实例；检查负载均衡 sticky session；检查 Redis Pub/Sub 或 MQ 广播通道；查看实例间消息日志。
- 修复建议: 使用 Redis/MQ 做跨实例广播；会话映射写入共享存储；网关启用粘性会话；推送结果可观测。

### WebSocket 经过网关返回 502/503/504
- 表现: 部分连接建立失败或长连接被网关中断。
- 错误码/日志关键词: `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`, `upstream prematurely closed connection`, `upstream timed out`
- 相关指标: gateway 5xx, upstream active connections, 后端连接数。
- 可能原因: 后端实例不可用，网关连接池耗尽，read timeout 配置不适合长连接，服务发现实例列表错误。
- 排查步骤: 检查网关 upstream 状态；检查服务发现健康检查；确认长连接 timeout；查看后端端口和路径。
- 修复建议: 网关长连接单独路由；提高 timeout；健康检查剔除异常实例；限制单用户连接数。

### 服务端连接数过高导致内存或线程耗尽
- 表现: 新连接失败，已有连接延迟升高。
- 错误码/日志关键词: `Too many open files`, `OutOfMemoryError`, `RejectedExecutionException`, `max connections exceeded`, `1001`, `1011 Internal Error`
- 相关指标: active connections, file descriptors, heap memory, thread pool queue。
- 可能原因: 连接泄漏，客户端重连风暴，单用户多连接，文件描述符限制低。
- 排查步骤: 统计连接数按用户/IP 分布；查看 fd 使用；检查重连频率；检查内存和线程池。
- 修复建议: 限制单用户连接数；重连退避；提升 fd 限制；连接关闭时清理 session；连接维度监控。

## Runbook

### WebSocket 断连排查流程
1. 收集 close code: `1006`, `1001`, `1008`, `1011`。
2. 判断失败阶段: 握手失败、连接后断开、心跳超时、消息发送失败。
3. 检查网关 Upgrade header、idle timeout 和 5xx。
4. 检查 token 过期、服务端连接数和实例重启。
5. 多实例场景检查会话路由和广播通道。

## Prevention
- 长连接路由和普通 HTTP 路由分开配置。
- 心跳间隔小于网关 idle timeout，并允许多次失败。
- 实现断线重连指数退避。
- 监控 active connections、close code 分布、握手失败率和消息发送失败率。
