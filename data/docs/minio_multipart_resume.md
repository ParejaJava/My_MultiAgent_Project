---
title: MinIO 分片上传与断点续传诊断知识库
category: object-storage
service: MinIO
severity: medium
tags:
  - minio
  - multipart-upload
  - resume-upload
  - large-file
  - object-storage
  - uploadId
  - ETag
error_codes:
  - NoSuchUpload
  - InvalidPart
  - InvalidPartOrder
  - EntityTooSmall
  - SignatureDoesNotMatch
  - XMinioInvalidObjectName
  - 400
  - 403
  - 404
  - 408
  - 413
  - 499
  - 500
  - 503
---

# MinIO 分片上传与断点续传诊断知识库

## Metadata
- component: MinIO
- category: object-storage
- tags: minio, multipart upload, resume upload, large file, object storage, uploadId, ETag
- common_errors: NoSuchUpload, InvalidPart, InvalidPartOrder, EntityTooSmall, SignatureDoesNotMatch, XMinioInvalidObjectName, 400, 403, 404, 408, 413, 499, 500, 503

## Overview
MinIO 常用于对象存储、大文件上传、分片上传和断点续传。上传链路通常涉及前端、网关、后端服务、MinIO SDK 和 MinIO Server。诊断时要同时检查 uploadId、partNumber、ETag、临时分片记录、网关超时、对象桶权限和 MinIO 服务端日志。

## Symptoms

### 分片上传初始化失败 CreateMultipartUpload 返回 403 或 SignatureDoesNotMatch
- 表现: 前端刚开始上传大文件时失败，无法获得 uploadId。
- 错误码/日志关键词: `403 Forbidden`, `SignatureDoesNotMatch`, `AccessDenied`, `InvalidAccessKeyId`, `The request signature we calculated does not match`, `X-Amz-Date`, `AuthorizationHeaderMalformed`
- 相关指标: MinIO `s3_requests_errors_total`, 网关 `4xx` 数量, 后端鉴权失败日志。
- 可能原因: AK/SK 配置错误，服务端时间偏移，桶策略无写入权限，网关改写 Host 或 Header，预签名 URL 过期。
- 排查步骤: 校验 MinIO endpoint、bucket、region、access key；检查服务器时间同步；确认桶策略允许 `s3:PutObject` 和 `s3:AbortMultipartUpload`；抓取请求头确认签名字段未被网关修改。
- 修复建议: 修正凭据和 endpoint；统一 NTP 时间；调整 bucket policy；网关转发时保留 Host、Authorization、x-amz-* 请求头。

### 上传分片失败 UploadPart 返回 400 InvalidPart 或 404 NoSuchUpload
- 表现: 部分分片上传成功，某个分片失败，重试后仍报错。
- 错误码/日志关键词: `400 InvalidPart`, `404 NoSuchUpload`, `NoSuchUpload`, `UploadPart`, `uploadId does not exist`, `The specified upload does not exist`
- 相关指标: MinIO `s3_requests_4xx_errors_total`, 后端分片状态表, 前端重试次数。
- 可能原因: uploadId 已被清理，断点续传记录过期，partNumber 与 uploadId 不匹配，用户重新初始化上传但继续使用旧分片状态。
- 排查步骤: 检查后端保存的 uploadId 是否与当前文件 hash 一致；查询 MinIO incomplete multipart upload；确认断点续传状态没有被清理任务删除；检查 partNumber 是否从 1 开始。
- 修复建议: 使用文件 hash、bucket、objectName 绑定 uploadId；断点续传时先校验 uploadId 是否存在；不存在时重新初始化并清理旧分片记录。

### CompleteMultipartUpload 合并失败 InvalidPartOrder 或 EntityTooSmall
- 表现: 所有分片上传完成，但最后合并对象失败。
- 错误码/日志关键词: `400 InvalidPartOrder`, `400 EntityTooSmall`, `InvalidPart`, `InvalidPartOrder`, `EntityTooSmall`, `CompleteMultipartUpload`
- 相关指标: 分片数量, 每片大小, ETag 列表, MinIO 合并失败日志。
- 可能原因: 分片列表未按 partNumber 升序提交，非最后一个分片小于 5MB，ETag 丢失或错误，重复提交了错误的 partNumber。
- 排查步骤: 打印 CompleteMultipartUpload 请求体；确认 partNumber 连续且升序；确认每个 part 的 ETag 来自 MinIO 返回值；检查最后一片之外的大小是否小于 5MB。
- 修复建议: 后端按 partNumber 排序后合并；保存每个分片真实 ETag；限制前端分片大小；合并前做分片完整性校验。

### 断点续传命中失败导致重复上传
- 表现: 用户刷新页面或网络中断后，系统没有复用已上传分片。
- 错误码/日志关键词: `NoSuchUpload`, `uploadId missing`, `resume upload failed`, `part cache miss`, `ListParts`, `404`
- 相关指标: 重复上传流量, uploadId 缓存命中率, 分片状态表记录数。
- 可能原因: 文件唯一标识不稳定，前端 hash 计算方式变化，后端未持久化 uploadId，缓存 Redis 过期太短，用户换桶或 objectName。
- 排查步骤: 对比同一文件多次上传的 fileHash；检查 Redis 或数据库中的 uploadId TTL；确认 objectName 生成规则是否稳定；调用 ListParts 验证已上传分片。
- 修复建议: 用文件 hash + size + bucket + objectName 作为续传 key；uploadId 记录持久化；恢复上传时以 MinIO ListParts 为准重建分片状态。

### 大文件上传经过网关返回 413 或 504
- 表现: 小文件正常，大文件或慢网络上传失败。
- 错误码/日志关键词: `413 Payload Too Large`, `504 Gateway Timeout`, `408 Request Timeout`, `499 Client Closed Request`, `client_max_body_size`, `upstream timed out`
- 相关指标: 网关 `4xx/5xx`, upstream 响应时间, 请求体大小, 客户端断开数。
- 可能原因: Nginx 或 API Gateway body size 限制，网关 idle timeout 太短，后端连接池不足，上传分片过大。
- 排查步骤: 检查 Nginx `client_max_body_size`、`proxy_read_timeout`、`proxy_send_timeout`；检查 Spring Gateway request size 限制；对比直连 MinIO 和经网关上传结果。
- 修复建议: 调整网关上传大小和超时；降低单片大小；上传接口绕过业务网关或使用预签名 URL 直传 MinIO。

### MinIO 服务端繁忙返回 503 SlowDown
- 表现: 高并发上传时分片随机失败，重试后成功。
- 错误码/日志关键词: `503 SlowDown`, `503 Service Unavailable`, `XMinioServerNotInitialized`, `too many requests`, `connection reset by peer`
- 相关指标: MinIO 磁盘 IO, CPU, 网络吞吐, `s3_requests_waiting_total`, 磁盘使用率。
- 可能原因: MinIO 节点负载过高，磁盘 IO 打满，上传并发过大，客户端重试风暴，纠删码集群节点异常。
- 排查步骤: 查看 MinIO console 节点状态；检查磁盘延迟和网络吞吐；统计客户端并发分片数；检查是否有大量未完成 multipart upload。
- 修复建议: 限制单用户并发分片数；加入指数退避重试；扩容 MinIO 节点或磁盘；定期清理未完成上传。

## Runbook

### MinIO 分片上传失败排查流程
1. 判断失败阶段: 初始化、上传分片、列出分片、合并、清理。
2. 收集错误码: `NoSuchUpload`, `InvalidPart`, `InvalidPartOrder`, `EntityTooSmall`, `SignatureDoesNotMatch`, `413`, `504`。
3. 检查 uploadId、partNumber、ETag 是否完整一致。
4. 检查网关大小限制和超时配置。
5. 检查 MinIO bucket policy、服务端负载、磁盘 IO。
6. 对失败文件执行 ListParts，确认 MinIO 真实分片状态。

## Prevention
- 分片大小建议大于 5MB，并保留最后一片例外。
- uploadId 与文件 hash、bucket、objectName 强绑定。
- CompleteMultipartUpload 前做 ETag 和 partNumber 完整性校验。
- 网关明确配置大文件上传 body size 和 timeout。
- 对 `503 SlowDown`, `408`, `499`, `504` 使用指数退避重试。
