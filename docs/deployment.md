# 多节点部署

> 跨部署段：网关、平台、独立进程、业务系统均按 × N 部署。相关：[总体架构](overview.md)、[网关与鉴权](gateway.md)、[业务与平台通信](communication.md)。

## 要点

- **进程无状态**：网关、平台、业务实例都不保存会话；身份靠 JWT / 签名头，任意节点可处理任意请求，不需要会话粘滞。
- **共享状态只放平台三件套**：PostgreSQL（业务数据、幂等、outbox、任务表）、Redis（计数、吊销、锁、广播）、MinIO（文件）；网关配置另在 etcd。节点本地只允许放可丢失、有 TTL 的缓存。
- **单例任务靠数据库约束**：对账、补偿、过期清理作为定时计划写入任务表，`(schedule_id, fire_time)` 唯一约束保证只触发一次；不在每个节点上跑 `@Scheduled`。
- **事件至少一次**：发送端用 Outbox，消费端按事件 ID 去重；多节点并发消费不会重复处理。
- **缓存失效靠事件**：配置变更发事件，各节点收到后清本地缓存；事件丢失时由 TTL 兜底。
- **纯 Docker 部署，不使用 K8s**：每台主机用 Docker Compose 运行容器，节点地址是「主机 IP:端口」的静态列表；服务发现、负载均衡、健康检查与滚动发布由 APISIX（入口流量）和平台客户端负载均衡（内部调用）承担。

## 部署方式（Docker）

### 本地运维控制台

本地开发 Compose 提供以下入口；etcd `2379` 仅绑定 `127.0.0.1`，三个控制台端口对局域网开放，供 HTTP 访问时运维看板直连：

| 控制台 | 地址 | 说明 |
|------|------|------|
| MinIO | `http://localhost:9001` | MinIO Console |
| APISIX | `http://localhost:9180/ui/` | APISIX 3.13+ 内嵌 Dashboard，使用 `.env` 中的 `APISIX_ADMIN_KEY` |
| etcd | `http://localhost:9010` | etcd Workbench；首次进入后添加 endpoint `http://etcd:2379` |

设 `VITE_HTTPS=true` 后，`start-service.sh` 还会启用 `ops-https` 反代：MinIO Console 使用 HTTPS 端口 `9444`，APISIX Dashboard / Admin API 使用 `9181`，etcd Workbench 使用 `9011`。`VITE_HTTPS=false` 时 `start-service.sh` 会移除该反代容器。运维看板按访问协议选择入口：HTTP 直连原端口，HTTPS 走 TLS 反代；Workbench 页面内配置 etcd 连接。运维入口应限制在可信网络，访问设备需信任 HTTPS 证书。APISIX 仍校验随机 `APISIX_ADMIN_KEY`，每台浏览器首次打开 Dashboard 时需在 Settings 中填写。浏览器预签名文件 URL 只含路径，经前端同源转发到 MinIO（见 [对象存储路径](storage.md)「访问规则」），无需单独暴露 S3 API。

etcd Workbench Web 版已停止维护，仅供本地开发调试；生产环境应限制管理入口网络访问。

| 项 | 约定 |
|----|------|
| 编排 | Docker 配置统一放在仓库 `docker/`；每台主机一份 Compose 文件，按角色划分主机：网关主机、平台主机、算子主机（GPU）、基础设施主机；不使用 K8s / Swarm |
| 镜像 | 统一推送到内网镜像仓库，标签用版本号，禁止 `latest`；编排文件按环境（测试 / 生产）分目录，纳入版本库 |
| 网络 | 容器端口映射到主机端口，跨主机直接用「主机 IP:端口」；主机防火墙只允许网关网段访问业务与平台端口 |
| 配置与密钥 | 非敏感配置用 `.env`；密钥用只读挂载的文件（权限 600），不写进镜像与编排文件 |
| 存活 | `restart: unless-stopped` + 容器 `healthcheck`；主机宕机由 APISIX 主动健康检查摘除节点 |
| 日志 | 容器 stdout → Loki（Docker 日志驱动或 Promtail）；指标经 OpenTelemetry → Prometheus |
| GPU | 算子主机安装 NVIDIA Container Toolkit，`deploy.resources.reservations.devices` 指定 GPU |
| 数据卷 | PostgreSQL、MinIO、etcd、Redis 使用主机本地盘挂载卷，不放在容器可写层 |

**节点清单是平台配置**：业务系统、平台、算子的节点列表都登记在平台（应用接入的 `gateway.upstream.nodes`、能力目录的提供方地址），由平台下发到 APISIX；扩容 = 新主机起容器 → 控制台加节点 → 健康检查通过后接流量。

**滚动发布**（单个节点逐一进行）：

1. 平台经 Admin API 把该节点权重置 0，等待在途请求结束（默认 30 秒，长连接按 SSE 超时）；
2. 每台主机使用对应角色的 Compose 文件执行 `docker compose --project-directory . -f <compose-file> pull && docker compose --project-directory . -f <compose-file> up -d` 替换容器（本地开发编排位于 `docker/docker-compose.yml`）；
3. 容器健康检查通过 → 恢复权重；失败则回滚到上一镜像标签；
4. 下一个节点。平台与 Worker 同理，Worker 收到 `SIGTERM` 后停止领取新任务，等当前任务完成或租约到期。

**内部调用的负载均衡**：平台调用算子节点不经网关，能力模块按目录中登记的节点列表做客户端负载均衡（轮询 + 被动熔断 + 每 10 秒主动探测 `/health`）。

## 各部署段的多节点问题

| 部署段 | 多节点问题 | 方案 |
|--------|-----------|------|
| 网关 APISIX × N | 配置一致 | 只经控制面 Admin API 写 etcd，数据面 watch，秒级一致；etcd 不可用时数据面继续用内存中的最后配置，只是无法变更 |
| | 限流计数分散 | `limit-count` 用 `policy: redis-cluster`，按 应用 × 租户 全局计数；Redis 不可用时 `allow_degradation` 放行并告警 |
| | 吊销状态 | `km-revoke` 查共享 Redis 吊销集合，节点无本地状态 |
| | JWKS 公钥 | 各节点本地缓存 JWKS（TTL 10 分钟），遇到未知 `kid` 立即刷新；密钥轮换新旧并存，节点刷新先后不影响验签 |
| | 健康检查 | 每个节点独立主动探测上游，结果不共享，不需要共享 |
| | 长连接（SSE / WebSocket） | 无需粘滞；发布时数据面优雅退出（`graceful_shutdown_timeout`），SDK 断线自动重连 |
| 平台 × N | 定时任务重复执行 | 全部改为任务表定时计划（见 [任务调度](platform/scheduler.md)）；数据库迁移由 Alembic 表锁保证只一个节点执行 |
| | 事件丢失或重复 | 各模块在自己的 schema 内建 `outbox` 表，与业务写同一事务；事件分发器用 `SELECT … FOR UPDATE SKIP LOCKED` 多节点并行领取并投递 |
| | 本地缓存不一致 | 能力点绑定、应用配置、权限计算结果：进程内 TTL 缓存 + 事件失效（`capability.binding.changed` 等，平台内部用 Redis pub/sub 广播到每个节点）+ TTL 兜底 |
| | 幂等键 | 存 PostgreSQL 唯一约束（如标注工单的 `Idempotency-Key`），不放内存 |
| | 配额计量 | Redis 原子计数做实时拦截，每分钟汇总落 PostgreSQL 作为计量账本 |
| | 文件上传 | MinIO 预签名 URL 直传，流量不经平台节点，不存在节点亲和 |
| | 滚动发布 | 表结构按「先扩后缩」演进：新增列可空 → 双写 → 切读 → 下个版本再删旧列，保证新旧版本共存 |
| platform-worker × N | 任务重复执行 | 任务表 `SKIP LOCKED` 竞争领取，租约 + 心跳，失联后由其他 Worker 接手；任务按业务键幂等 |
| 算子节点 × N | 负载与 GPU 分配 | 同步调用由能力模块按节点列表客户端负载均衡；异步调用由 Worker 领取任务后同步调用，Redis 信号量控制 算子 × 租户 并发；按算子独立扩缩 |
| edge-agent × N | 现场网络不稳定 | 只发起出站 HTTPS（经网关批量上报、长轮询取指令），本地缓存 + 按序号断点续传，不需要平台反向访问现场 |
| 业务系统 × N | 事件重复投递到不同节点 | SDK 内置 `km_event_inbox` 表按 CloudEvents `id` 唯一约束去重，处理与业务写同一事务 |
| | 补偿轮询重复 | SDK 补偿任务用 PostgreSQL advisory lock（或 ShedLock）选一个节点执行 |
| | 权限缓存 | 统一权限组件按 `sub` 本地缓存 5 分钟；绑定变更时通过本系统 Redis pub/sub 通知所有节点失效，见 [统一权限组件](platform/auth/authz.md) |
| | Service Token | 每个节点各自换取并缓存，到期前 20% 刷新；认证模块不限制同一 client 的并发 Token 数 |

## 基础设施高可用

| 组件 | 最小高可用形态 |
|------|---------------|
| PostgreSQL + pgvector | 主从流复制 + 自动切换（Patroni，容器化部署），应用连 Keepalived VIP |
| Redis | Redis Cluster 3 主 3 从，或哨兵 1 主 2 从 |
| MinIO | 分布式模式 ≥ 4 盘纠删码 |
| etcd（网关） | 3 节点 |

## 降级策略

| 依赖故障 | 影响 | 行为 |
|----------|------|------|
| etcd | 不能改路由 | 数据面用最后配置继续服务；应用接入保存进入「待下发」 |
| Redis | 吊销、限流失效；缓存与广播丢失 | 网关降级放行并告警，靠 15 分钟短 Token 兜底；平台缓存回源 PostgreSQL，本地缓存靠 TTL 兜底 |
| 认证模块 | 不能登录、换 Token | 已签发 Token 在有效期内继续可用（网关本地验签） |
| PostgreSQL | 平台不可写 | 主从自动切换（秒级到分钟级）；切换期间写接口返回 `503`，outbox 与任务均在库内，切换后继续，不丢 |
| 平台整体 | 能力调用失败 | 业务系统核心功能（档案浏览、检索）不依赖平台在线；需要平台的操作给出明确提示 |
