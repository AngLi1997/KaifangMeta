# 应用接入

> 平台 · 认证模块。应用描述是持久配置来源：OIDC 客户端、APISIX 路由、事件订阅由应用接入配置下发并定时对账；运维可直接使用 APISIX Dashboard，但手工改动可能被对账覆盖且不会写入平台审计。相关：[网关与鉴权](../../gateway.md)、[鉴权流程](../../auth-flow.md)、[统一认证与身份](identity.md)、[统一门户](portal.md)、[SDK](../../sdk.md)。

## 要点

- **一个业务系统 = 一个应用**：一个 `client_id`、一份应用描述（OIDC、网关路由、平台权限、事件、门户），存认证模块 `iam` schema，控制台「应用接入」是唯一维护入口，YAML 只用于环境迁移。
- **新应用接入身份认证只做三件事**：前端引入 `kaifang-meta-shell` 完成 OIDC 登录；后端引入 SDK 按鉴权模式拿到 `sub` / `tid`；按 `sub` 关联本地用户。业务系统不存密码、不做登录页。
- **能否进入应用由平台判定，进入后能做什么由业务判定**：应用访问 = 应用可用 ∧ 租户已开通 ∧（访问范围为全员 ∨ 用户在应用成员名单）；角色、菜单、数据权限仍归业务系统。
- 授权页 `/authorize`、Refresh Token 续期和统一门户共用同一个访问判定，名单移除后最迟一个 Access Token 有效期（15 分钟）内失效。
- 应用管理覆盖注册、配置、租户开通、成员名单、密钥轮换、上下线、接入自检，按超管 / 租户管理员 / 应用管理员分权。

## 新应用接入身份认证

### 按应用类型选择接入方式

| 类型 | 用户登录 | 后端拿身份 | 平台登记 |
|------|----------|------------|----------|
| `web`（前端 + 后端） | 前端壳 `kaifang-meta-shell`：授权码 + PKCE，Token 只存内存 | 模式 A 读网关签名身份头（默认）；模式 B 用 JWKS 验 JWT | 回调地址、退出回调、网关前缀与上游 |
| `service`（纯后端） | 无 | Service Token（client credentials） | 网关前缀与上游、`callers`、平台 scope |
| `desktop` | 系统浏览器 + 本地回调，见 [Agent 桌面端](../../harness.md) | 无业务后端 | 回调地址、客户端发布 |
| `third-party` / 存量 | 自有登录（模式 C），可选把平台作为外部 OIDC IdP | 自有会话 | 迁移期限 |

### 前端

```ts
import { createShell } from 'kaifang-meta-shell'

const shell = createShell({
  issuer: '/kaifang-meta/iam',
  clientId: 'kaifang-meta-archive-room',
  redirectUri: `${location.origin}/callback`,
})
await shell.ready()          // 无会话 → 跳登录；有 SSO 会话 → prompt=none 静默换本应用 Token
shell.fetch('/kaifang-meta/archive/api/me')   // 自动带 Bearer、到期前续期
```

- 从门户进入时同一 SSO 会话、沿用当前租户，不再出现登录页；直接打开应用地址时同样适用。
- 退出调用 `shell.logout()`：结束 SSO 会话，所有应用同时退出。
- 浏览器只持有本应用 Access Token；`client_secret`、`gateway_secret`、Service Token 只在后端。

### 后端

```yaml
kaifang-meta:
  issuer: https://gw.internal/kaifang-meta/iam
  client-id: kaifang-meta-archive-room
  client-secret: ${KM_CLIENT_SECRET}
  auth-mode: gateway              # 与平台登记一致；SDK 启动时校验
  gateway-secret: ${KM_GATEWAY_SECRET}
  event-secret: ${KM_EVENT_SECRET}
  rbac.enabled: true              # 可选统一权限组件，数据存本业务库，见 authz.md
```

Java 引入 `kaifang-meta-spring-boot-starter` 后自动获得：身份过滤器（按模式验签名或验 JWT）、`KmContext.user() / tenant()`、`KmDirectory`、`KmCapability`、`KmAnnotation`、`@KmEventListener("annotation.task.completed")`、审计日志切面。Python 使用同名环境变量 `KM_ISSUER`、`KM_CLIENT_ID` 等，提供 FastAPI / Django 中间件。协议细节见 [SDK](../../sdk.md)。

### 本地用户关联

| 方式 | 时机 | 做法 |
|------|------|------|
| 首次访问自动建档 | 请求带来未知 `sub` | SDK 回调 `KmUserProvisioner`：用 `KmDirectory` 取登录名、姓名、邮箱建本地用户，**不授予任何角色**，前端显示“待分配权限” |
| 管理员预建 | 业务的用户管理页 | 按登录名查身份目录（`GET /kaifang-meta/platform/iam/v1/accounts?username=`）得到 `sub` 后建本地用户并授角色 |
| 事件同步 | 订阅 `user.*`、`app.access.*` | `user.disabled` / `user.deleted` 禁用本地用户；`app.access.revoked` 清理本地授权 |

本地用户表以 `sub` 为唯一键，不用登录名、手机号关联；本地资料是业务副本，由业务自行更新。

### 应用访问判定

认证模块提供一个判定，`/authorize`、`refresh_token` 续期、门户“我的应用”共用：

```text
can_access(sub, tid, client) =
    client.status == online                      # testing 仅限成员名单
  ∧ tid ∈ client.tenants                         # 租户已开通
  ∧ (client.access == all ∨ (client_id, tid, sub) ∈ iam.app_member)
```

| 失败情形 | `/authorize` | 续期 | 门户 |
|----------|--------------|------|------|
| 应用停用 | 503 页“应用维护中” | `invalid_grant` | 灰显“维护中” |
| 租户未开通 | 403 `TENANT_NOT_ENABLED` | `invalid_grant` | 不显示 |
| 不在成员名单 | 403 `APP_ACCESS_DENIED` | `invalid_grant` | 不显示 |

- 判定只决定“能否进入”，不产生业务角色；业务系统对已进入但无本地角色的用户自行拒绝或引导申请。
- Service Token 不经此判定，按应用的 `platform_access` 与 `callers` 授权。
- 名单增删写入 outbox `app.access.granted` / `app.access.revoked`（只带 `client_id`、`tenant_id`、`sub`），仅投递给该应用。

## 接入对象：应用描述

控制台「应用接入」页面是主入口，同时支持导出 / 导入 YAML，用于 测试 → 生产 的环境迁移（不同环境的密钥不同、不随 YAML 导出）。

```yaml
app: archive-room
client_id: kaifang-meta-archive-room
name: 智慧档案室
owner: { team: 档案业务组, contact: u_2011 }
type: web                       # web | service | desktop（见 ../../harness.md）| third-party

tenants: [t_5e2a9c1d7b3f4086]   # 开通的租户
access: all                     # all：开通租户全员可进入 | members：仅成员名单（名单不随 YAML 导出）

auth:
  mode: gateway                 # gateway | passthrough | self
  public_paths: [/health, /public/**]
  migrate_by: null              # mode=self 时必填

oidc:
  redirect_uris: [https://archive.internal/callback]
  post_logout_redirect_uris: [https://archive.internal/]
  grant_types: [authorization_code, refresh_token, client_credentials]
  pkce: required

gateway:
  prefix: /kaifang-meta/archive
  routes:                       # 子路径 → 上游；网关去掉 prefix 后转发，一个应用可有多套后端
    - path: /api
      nodes: [10.20.3.11:8080, 10.20.3.12:8080]   # Docker 主机 IP:映射端口
      health: /api/actuator/health
  public_paths: [/api/actuator/health]
  rate_limit: 200               # 每租户 QPS
  callers: [kaifang-meta-doc-process]        # 允许调用本应用的其他应用

platform_access:                # 本应用的服务账号可调用的平台能力
  scopes: [directory:read, capability:invoke, annotation:task.write, events:subscribe]
  bindings: [archive.import.ocr, archive.import.extract, archive.qa.agent]

events:
  endpoint: https://archive.internal/kaifang-meta/events
  subscribe: [user.*, app.access.*, annotation.*, capability.binding.changed]

annotation:                     # 使用数据标注时填写，见 数据标注
  file_resolver: https://archive.internal/kaifang-meta/annotation/files:resolve
  embed_origins: [https://archive.internal]

portal:                         # 门户展示，见 portal.md
  icon: 档                      # 1–2 个字或图标名
  entry: https://archive.internal/
  description: 著录 · 检索 · 问答
  order: 20
```

### 存储（`iam` schema）

| 表 | 内容 |
|----|------|
| `iam.client` | 现有 OIDC 字段 + `status`、`auth_mode`、`access`、`owner`、`gateway`（JSON：前缀、子路由与上游、健康检查、公开路径、限流、`callers`）、`gateway_secret`、`sync_status` / `synced_at`、`portal`（JSON） |
| `iam.client_secret` | `client_id × kind（client / gateway / event）× 版本`：`client` 存哈希，`gateway` / `event` 需参与 HMAC 存明文（运行时数据库账号可读，不进日志与导出）；`expires_at` 支持双密钥重叠 |
| `iam.app_member` | `client_id × tenant_id × sub` 唯一，`granted_by`、`created_at`；只在 `access=members` 时生效 |

`iam.client` 现有 `event_secret` 迁入 `iam.client_secret`。应用描述的变更经控制台接口落审计日志，详情记录前后差异（密钥字段脱敏）。

## 应用管理

控制台菜单「认证 / 应用接入」，原型 `#apps`。

| 区域 | 内容 |
|------|------|
| 列表 | 应用、`client_id`、类型、鉴权模式、开通租户、访问范围、状态；操作：配置、上线 / 停用、导出 |
| 注册应用 | 分步表单：基本信息 → 鉴权与回调 → 网关上游 → 平台权限 → 事件 → 门户；完成后一次性显示 `client_secret`、`gateway_secret`、`event_secret` |
| 详情 · 接入配置 | 应用描述各段，按段编辑并下发 |
| 详情 · 租户与成员 | 开通租户；`access=members` 时按租户维护成员名单（按登录名搜索身份账号添加） |
| 详情 · 密钥 | 三类密钥当前版本、创建时间、轮换（新密钥只显示一次，旧密钥到 `expires_at` 作废） |
| 详情 · 接入自检 | JWKS 可达、网关签名、健康检查、事件投递、示例能力调用 |
| 详情 · 运行概况 | 实例健康、近 24 小时请求量 / 错误率、Token 签发量、事件投递与死信 |

| 角色 | 范围 | 可做 |
|------|------|------|
| 超级管理员 | `system` | 全部：注册、改任何段、上下线、轮换密钥、导入导出 |
| 租户管理员 | `tenant` | 本租户对已上线应用的开通 / 关闭，维护本租户成员名单 |
| 应用管理员 | `app` | 本应用的回调、上游、公开路径、事件、门户、自检；scope / 能力点 / `callers` 变更提交超管审批 |

控制台接口（前缀 `/kaifang-meta/console/api/v1/app`，按钮权限码同路径）：

| 接口 | 说明 |
|------|------|
| `GET /list`、`GET /get?client_id=` | 列表、详情（不含密钥明文） |
| `POST /create` | 注册，响应体含一次性密钥 |
| `POST /update` | 按段更新应用描述，保存后下发 |
| `POST /status` | `testing` / `online` / `disabled` / `retired` |
| `POST /secret/rotate` | `kind` + 重叠天数（默认 7） |
| `GET /member/list`、`POST /member/add`、`DELETE /member/delete` | 成员名单（按 `tenant_id`） |
| `POST /tenant/update` | 开通 / 关闭租户 |
| `POST /check` | 接入自检 |
| `GET /export`、`POST /import` | YAML |

## 平台期望状态与下发

- 控制台保存应用描述后，由认证模块下发三类配置：
  1. **OIDC 客户端** → 认证模块自身；
  2. **APISIX 路由 / 上游 / 插件** → 通过 APISIX Admin API 写入（etcd 是派生数据），资源名 `routes/km-app-<client_id>`、`upstreams/km-app-<client_id>`；
  3. **事件订阅** → 事件分发器。
- 后台对账任务每 5 分钟比对平台配置与 APISIX 实际配置，发现漂移则告警并以平台为准修复；Dashboard 的手工变更可能因此被覆盖。
- 下发失败时应用描述照常保存并标记“待下发”，由对账任务退避重试。

## 接入流程

| 步骤 | 执行方 | 产出 |
|------|--------|------|
| 1 注册应用 | 平台管理员 | `client_id`、三类密钥（仅显示一次），状态 `testing` |
| 2 选择鉴权模式、开通测试租户、指定应用管理员 | 平台管理员 + 业务负责人 | 路由插件组合 |
| 3 配置上游与回调 | 业务开发 / 应用管理员 | 网关路由生效（测试环境） |
| 4 前端引入 shell、后端引入 SDK、实现本地用户关联 | 业务开发 | 见上文「新应用接入身份认证」 |
| 5 申请平台能力 | 业务开发 → 平台审批 | scopes、能力点、配额 |
| 6 联调自检 | 业务开发 | 「接入自检」全部通过；`testing` 期间仅成员名单可登录 |
| 7 上线 | 平台管理员 | 导入生产环境 YAML，生成生产密钥，状态 `online`，门户可见 |

## 客户端发布

`desktop` 类型的应用额外有「客户端发布」：维护版本、渠道、灰度、最低支持版本与安装包，并生成公开下载主页。设计见 [Agent 桌面端](../../harness.md)。

## 生命周期与运维

- 状态：`testing（联调中）→ online（已上线）→ disabled（已停用）→ retired（已下线）`。停用时网关返回 503、授权页提示维护中并保留配置；下线后删除网关路由、吊销该应用全部 Refresh Token，`client_id` 不复用。
- **密钥轮换**：三类密钥均支持双密钥并存（默认 7 天重叠期），业务滚动发布后再作废旧密钥。
- 模式 C（业务自管）应用在列表中标注迁移期限，到期前 30 天提醒。

## 实现状态

| 项 | 状态 |
|----|------|
| OIDC 客户端、`iam.client`、CLI `create-client`（含门户字段）、按租户开通校验 | 已实现 |
| 统一门户，见 [统一门户](portal.md) | 部分实现 |
| 控制台网关路由下发（仅内置控制台与平台 API） | 已实现 |
| 控制台「应用接入」页面与接口（列表、注册、编辑、上线 / 停用、重新下发、轮换密钥）、业务应用路由下发（APISIX Admin API，etcd 持久化）、漂移检测、实例健康探测，见 [统建系统接入](onboarding-unified-build.md) | 已实现（迁移 `0022`；状态 `online` / `disabled`） |
| `gateway_secret` 存 `iam.client`，轮换无重叠期 | 已实现；`iam.client_secret` 双密钥重叠设计中 |
| 应用访问判定中的成员名单与 `testing` / `retired` 状态、`iam.app_member` | 设计中 |
| 定时对账、YAML 导入导出、接入自检、按租户 / 应用管理员分权 | 设计中 |
