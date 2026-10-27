# 算子

> 独立进程 `kaifang-meta-operator × N`（GPU / 异构依赖，按算子独立镜像）。相关：[能力目录](catalog.md)、[能力点](binding.md)。

## 单算子设计

- 每个算子是独立镜像，实现统一协议：
  - `GET /meta`：名称、版本、输入输出 JSON Schema、资源需求
  - `GET /health`
  - `POST /invoke`：同步调用；异步调用由平台 Worker 领取任务后再同步调用算子，算子本身不接队列
- 在能力中心注册并带语义化版本；能力中心负责路由、配额、计量、灰度与回滚。
- 按 GPU / CPU 资源池水平扩容。

## 复用方式

1. 业务系统经 SDK 按能力点调用，见 [能力点](binding.md)
2. 多个算子编排为流水线，由平台 Worker 按 PostgreSQL 任务表执行（见 [任务调度](../scheduler.md)）
3. 以 MCP 工具形式暴露给 Agent
