# 总体架构

架构图：[design/architecture.html](design/architecture.html)。

## 部署段

系统只拆为三个部署段，全部以 Docker 容器部署（不使用 K8s），见 [多节点部署](deployment.md)：

| 部署段 | 形态 | 说明 |
|--------|------|------|
| 网关 | APISIX × N（开源，不自研） | 无状态多节点，前置 SLB / VIP |
| 平台 | 模块化单体 kaifang-meta-platform × N | 认证、能力、AI、数据采集、数据标注、任务调度六个模块 |
| 业务系统 | 各自独立部署 | 智慧档案室、文书加工系统、统建系统、库房管理 |

平台内部按模块隔离：每个模块独立 schema，模块间只走接口调用，不跨模块访问表，后续可按需拆出。

以下四类是平台的**独立进程**（部署形态，不算业务服务）：

- **算子节点** `kaifang-meta-operator × N`：GPU / 异构依赖，按算子独立镜像
- **kaifang-meta-platform-worker × N**：与平台同一代码库，不同启动入口，从 PostgreSQL 任务表领取并执行异步任务与流水线
- **kaifang-meta-edge-agent × N**：部署在现场，对接硬件
- **kaifang-meta-weknora × N** + **kaifang-meta-docreader × N**：开源 WeKnora，AI 模块的知识库与 Agent 引擎，只在内网由 AI 模块调用，见 [WeKnora](platform/capability/weknora.md)

## 平台模块

| 模块 | 文档 |
|------|------|
| 认证 | [统一认证与身份](platform/auth/identity.md)、[应用接入](platform/auth/app-onboarding.md)、[统一权限组件](platform/auth/authz.md) |
| 能力 | [能力目录与下放](platform/capability/catalog.md)、[能力点](platform/capability/binding.md)、[算子](platform/capability/operator.md) |
| AI | [知识库与 Agent 版本](platform/capability/knowledge-agent.md)、[知识库与 Agent 引擎（WeKnora）](platform/capability/weknora.md) |
| 数据采集 | [数据采集](platform/ingest.md) |
| 数据标注 | [数据标注](platform/annotation/overview.md) |
| 任务调度 | [定时任务与异步处理](platform/scheduler.md) |

## 跨段设计

- [网关与鉴权](gateway.md)（含 APISIX 集成）、[鉴权流程](auth-flow.md)
- [业务与平台通信](communication.md)：通道、接口约定、端到端时序、事件投递
- [多应用设计](apps.md)：应用清单、应用间与应用 ↔ 平台通信、数据与文件归属
- [多节点部署](deployment.md)：各部署段多节点问题与高可用
- [Agent 桌面端](harness.md)：配套客户端的认证、能力使用、版本发布与下载主页

## 基础设施

**平台基础设施只有三件：PostgreSQL + pgvector、Redis、MinIO。** 不引入消息队列、工作流引擎、独立向量库与 MQTT Broker，队列、调度、事件都落在这三件上。

| 组件 | 承担 | 替代了 |
|------|------|--------|
| PostgreSQL + pgvector | 各模块业务数据（独立 schema）、事件 outbox 与投递记录、任务表与流水线状态、幂等记录、计量账本、向量索引（HNSW） | RabbitMQ（事件持久化与重试）、Temporal（任务与工作流状态）、Milvus |
| Redis | 缓存、Token 吊销集合、Refresh Token、限流与配额计数、分布式锁与并发信号量、节点间缓存失效广播（pub/sub） | RabbitMQ fanout |
| MinIO | 文件、原始区、标注快照、数据集与模型产物 | — |

- **事件**：模块写业务数据时在同一事务写 outbox；事件分发器多节点以 `FOR UPDATE SKIP LOCKED` 领取并 HTTP 投递，`LISTEN / NOTIFY` 唤醒降低延迟。见 [业务与平台通信](communication.md)。
- **调度与工作流**：PostgreSQL 任务表 + 租约，见 [任务调度](platform/scheduler.md)。
- **向量**：pgvector，按知识库版本分表或分区；单库超过千万级向量时为该租户独立部署平台。
- **设备上报**：edge-agent 经网关 HTTPS 批量上报，见 [数据采集](platform/ingest.md)。

不属于平台基础设施、但部署时需要的组件：网关配置存储 etcd（APISIX 自带依赖）、镜像仓库、可观测栈（OpenTelemetry、Prometheus、Loki、Grafana）。

## 命名约定

部署进程、镜像、SDK 包、应用 client_id 统一以 `kaifang-meta-` 为前缀，网关路由统一挂在 `/kaifang-meta/` 下。
