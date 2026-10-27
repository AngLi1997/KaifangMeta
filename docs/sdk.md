# SDK / Starter 分发

> 本文定义 Python SDK、Java Starter 与前端包的目标能力及边界。相关：[应用接入](platform/auth/app-onboarding.md)、[鉴权流程](auth-flow.md)、[业务与平台通信](communication.md)、[统一权限组件](platform/auth/authz.md)、[数据标注对接](platform/annotation/integration.md)。

## 要点

- SDK 源码按语言放在 `sdk/` 下；各包独立构建、独立语义化版本，通过对应私服发布。
- 后端包统一处理身份上下文、Service Token、REST 通信和事件验签；平台业务客户端按应用申请的 scope 使用。
- 事件至少一次投递；SDK 提供 HMAC 验签、持久化去重与回查辅助，业务仍维护自己的流程状态。
- RBAC 组件可复用，但角色、菜单、用户关系和数据均存于使用方自己的数据库。
- 浏览器包处理用户登录与平台页面嵌入；浏览器永远不持有 Service Token 或应用密钥。
- SDK 不接管业务状态机、业务数据、对象存储或业务数据范围规则。

## 包与发布

| 语言 | 包 | 源码目录 | 分发 |
|------|----|----------|------|
| Python | `kaifang-meta-sdk` | `sdk/python/kaifang-meta-sdk/` | PyPI 私服 |
| Java | `kaifang-meta-spring-boot-starter` | `sdk/java/kaifang-meta-spring-boot-starter/` | Maven 私服 |
| TypeScript | `kaifang-meta-shell` | `sdk/typescript/kaifang-meta-shell/` | npm 私服 |
| TypeScript | `@kaifang-meta/sdk` | `sdk/typescript/kaifang-meta-sdk/` | npm 私服；标注页面嵌入辅助包 |

每个包有独立构建配置和版本；平台 REST 主版本由 URL 路径控制，SDK 包版本独立演进。OpenAPI 契约作为客户端生成源，兼容变更只增加字段，不静默改变既有字段语义。

## 后端公共核心

Python SDK 与 Java Starter 提供相同的核心协议能力，并遵循应用登记的 `auth.mode`。

| 能力 | 约定 |
|------|------|
| 身份验证 | `gateway` 模式校验网关签名身份头与时间窗；`passthrough` 模式以 JWKS 校验 JWT 的签名、发行方、有效期和 `aud`；`self` 模式不接管业务自身认证。默认使用 `gateway`。 |
| 请求上下文 | 提供请求级 `KmContext`：`sub`、`tid`、`client_id`、`principal_type`、`request_id`、`on_behalf_of`。上下文只在当前请求内有效；角色、菜单和权限不从 Token 或身份头推导。 |
| 配置 | 校验 `issuer`、`client_id`、认证模式和密钥；生产环境拒绝空值与默认密钥。应用密钥不写日志、不回传浏览器。 |
| Service Token | 后端以 client credentials 换取 Token，按应用、租户和 scope 缓存并在到期前续期；调用方只能申请应用获批的 scope。 |
| HTTP 客户端 | 基于 OpenAPI 提供类型化客户端；统一处理错误响应、超时、`X-KM-Request-Id` 与 `traceparent`。写请求由业务传入稳定的 `Idempotency-Key`；仅对幂等请求重试，尊重 `Retry-After`，默认最多重试两次。 |
| 身份目录 | `KmDirectory` 按 `sub` 查询账号基础资料及状态；不提供业务组织、业务角色或数据权限。 |
| 审计上下文 | 为业务自己的审计记录提供 `sub`、调用方、租户、代表用户和 request ID；Java 提供可选审计注解 / 切面；不把全部业务操作日志写入 Meta 审计库。 |

Java 配置示例：

```yaml
kaifang-meta:
  issuer: https://gw.internal/kaifang-meta/iam
  client-id: kaifang-meta-archive-room
  client-secret: ${KM_CLIENT_SECRET}
  auth-mode: gateway
  gateway-secret: ${KM_GATEWAY_SECRET}
  event-secret: ${KM_EVENT_SECRET}
  rbac:
    enabled: true
```

未启用事件或 RBAC 的应用可关闭对应功能；不要为未使用的能力配置额外密钥或申请 scope。

## 事件接收与恢复

- 校验 `X-KM-Event-Sign`、`ce-id`、`ce-time` 和 CloudEvents 消息体；签名使用 HMAC-SHA256，接受时间窗为 ±5 分钟，并在双密钥轮换期同时尝试新旧密钥。
- 通过 `KmEventListener` 按事件类型分发。先把事件 ID 持久化到业务本地 inbox，再返回成功；重复的 `ce-id` 不重复执行业务处理。
- 事件只作为状态变更通知。收到事件后，业务调用对应查询接口获取最新状态，不依赖事件到达顺序或事件体作为最终结果。
- 提供可选补偿轮询接口：业务传入本地待处理记录查询器和状态回查处理器，默认每 10 分钟核对一次。SDK 不创建或管理业务的 `run_id`、`task_id` 与批次映射表。

业务事件处理应先快速持久化，再异步执行较长的业务操作；只有持久化成功后才确认事件送达。

## 平台功能客户端

| 客户端 | 主要功能 | 使用边界 |
|--------|----------|----------|
| `KmDirectory` | 按 `sub` 读取身份账号基础资料 | 组织、角色和用户档案由业务系统维护 |
| `KmCapability` | 短时同步调用；异步创建 `run`、查状态、分页取结果 | 长任务不占用 HTTP 请求线程；业务保存 run 与业务记录的映射 |
| `KmAnnotation` | 建工单、分片提交清单、指派成员、查进度、拉取结果、导出、`ack`、返工 | 业务负责档案只读锁、结果校验与回写；方法需支持幂等键 |
| `KmAnnotationFileResolver` | 验证 Meta 对文件签发接口的 HMAC 请求，并将已验证请求交给业务处理 | 业务校验文件归属并签发短期 URL；SDK 不持有业务对象存储凭据 |

这些客户端只在应用获批对应 scope 后启用。同步调用限于短操作；批量处理、能力运行和标注工单均按 `202 + id`、状态查询和事件通知处理。具体接口见[业务与平台通信](communication.md)和[数据标注对接](platform/annotation/integration.md)。

## 本地 RBAC 组件

- 后端提供权限清单同步、`check` / `scopes_of`、缓存失效及 `@KmPermission("capability:publish")` 等接口。
- 前端 Shell 提供按权限渲染菜单和操作的组件，以及角色、菜单、绑定和审计管理页面。
- 权限数据存于使用方自己的库或 schema：平台控制台使用 `console_authz`，业务系统使用本业务库。SDK 不提供中心授权服务。
- 业务系统仍需自行实施记录级数据范围、租户隔离和业务资源授权；前端隐藏按钮不能代替后端鉴权。

## 前端包

`kaifang-meta-shell` 提供 OIDC Authorization Code + PKCE 登录、回调校验、静默恢复、Refresh Token 轮换、退出、租户切换、应用入口、动态菜单与权限组件。Access Token 只保存在内存中；业务前端只配置应用 ID、路由和主题，不接触 client secret 或 Service Token。

`@kaifang-meta/sdk` 提供平台页面嵌入辅助：`openAnnotation(taskId, { mode: 'tab' | 'iframe', view })`，处理 iframe 高度和 `postMessage`。父页面只把消息用于界面刷新，业务状态以事件和查询 API 为准；iframe 必须使用登记的 `annotation.embed_origins`。

## 业务边界

业务系统继续拥有本地用户资料、组织、角色、菜单、数据范围、领域状态机和审计记录。SDK 不实现业务流程、不替业务持有数据库连接、不替业务生成文件归属规则，也不把大文件代理经过平台服务。业务文件默认留在业务对象存储，通过短期预签名 URL 直传或直读。

接入流程与配置字段见[应用接入](platform/auth/app-onboarding.md)。`desktop` 类型应用的发布、渠道、灰度和下载页见 [Agent 桌面端](harness.md)。
