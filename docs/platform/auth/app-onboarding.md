# 应用接入

> 平台 · 认证模块。应用描述是持久配置来源：OIDC 客户端、APISIX 路由、事件订阅由应用接入配置下发并定时对账；运维可直接使用 APISIX Dashboard，但手工改动可能被对账覆盖且不会写入平台审计。相关：[网关与鉴权](../../gateway.md)、[统一认证与身份](identity.md)。


## 接入对象：应用描述

一个业务系统在平台中登记为一个**应用**，所有配置集中在一份应用描述中。控制台“应用接入”页面是主入口，同时支持导出 / 导入 YAML，用于 测试 → 生产 的环境迁移（不同环境的密钥不同、不随 YAML 导出）。

```yaml
app: archive-room
client_id: kaifang-meta-archive-room
name: 智慧档案室
owner: { team: 档案业务组, contact: u_2011 }
type: web                       # web（前端+后端）| service（纯后端）| desktop（桌面客户端，见 ../../harness.md）| third-party

tenants: [t_5e2a9c1d7b3f4086]            # 开通的租户

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
  upstream:
    nodes: [10.20.3.11:8080, 10.20.3.12:8080]   # Docker 主机 IP:映射端口
    health_check: { path: /actuator/health, interval: 5s }
  rate_limit: { per_tenant_qps: 200 }
  callers: [kaifang-meta-doc-process]        # 允许调用本应用的其他应用

platform_access:                # 本应用的服务账号可调用的平台能力
  scopes: [directory:read, capability:invoke, annotation:task.write, events:subscribe]
  bindings: [archive.import.ocr, archive.import.extract, archive.qa.agent]

events:
  endpoint: https://archive.internal/kaifang-meta/events
  subscribe: [user.*, annotation.*, capability.binding.changed]

annotation:                     # 使用数据标注时填写，见 数据标注
  file_resolver: https://archive.internal/kaifang-meta/annotation/files:resolve   # 引用模式的文件签发接口
  embed_origins: [https://archive.internal]                                        # 允许 iframe 嵌入标注页面的来源

portal:
  icon: archive
  entry: https://archive.internal/
```

门户只展示当前用户可访问的应用，不按平台组织树筛选；业务系统进入后再按本系统组织与权限控制菜单及数据。

## 平台期望状态与控制台操作

- 控制台保存应用描述后，由认证模块下发三类配置：
  1. **OIDC 客户端** → 认证模块自身；
  2. **APISIX 路由 / 上游 / 插件** → 通过 APISIX Admin API 写入（etcd 是派生数据）；
  3. **事件订阅** → 事件分发器。
- 后台对账任务每 5 分钟比对平台配置与 APISIX 实际配置，发现漂移则告警并以平台为准修复；Dashboard 的手工变更可能因此被覆盖。
- Dashboard 手工操作不经过平台审计。需要长期保留的变更应同步更新平台应用描述；平台下发的变更记审计日志（谁、何时、改了什么、前后差异）。

## 接入流程

| 步骤 | 执行方 | 产出 |
|------|--------|------|
| 1 注册应用 | 平台管理员 | `client_id`、`client_secret`、`gateway_secret`、`event_secret`（仅显示一次） |
| 2 选择鉴权模式、开通租户 | 平台管理员 + 业务负责人 | 路由插件组合 |
| 3 配置上游与回调 | 业务开发 | 网关路由生效（测试环境） |
| 4 引入 SDK | 业务开发 | 见下文“SDK 接入示例” |
| 5 申请平台能力 | 业务开发 → 平台审批 | scopes、能力点、配额 |
| 6 联调自检 | 业务开发 | 控制台“接入自检”：JWKS 可达、签名校验通过、健康检查通过、事件投递成功、示例能力调用成功 |
| 7 上线 | 平台管理员 | 导入生产环境 YAML，生成生产密钥，门户入口可见 |

## SDK 接入示例

**Java（Spring Boot）**

```yaml
kaifang-meta:
  issuer: https://gw.internal/kaifang-meta/iam
  client-id: kaifang-meta-archive-room
  client-secret: ${KM_CLIENT_SECRET}
  auth-mode: gateway              # 与平台配置一致；SDK 启动时会校验
  gateway-secret: ${KM_GATEWAY_SECRET}
  event-secret: ${KM_EVENT_SECRET}
  rbac.enabled: true              # 可选统一权限组件，数据存本业务库，见 authz.md
```

引入 `kaifang-meta-spring-boot-starter` 后自动获得：身份过滤器（按模式验签名或验 JWT）、`KmContext.user() / tenant()`、`KmDirectory`、`KmCapability`、`KmAnnotation`、`@KmEventListener("annotation.task.completed")`、审计日志切面。

**Python**：同名环境变量 `KM_ISSUER`、`KM_CLIENT_ID` 等；提供 FastAPI / Django 中间件。

**前端**：`kaifang-meta-shell` 负责 OIDC 登录跳转、静默续期、门户导航与退出；业务只提供路由与主色。

## 客户端发布

`desktop` 类型的应用额外有「客户端发布」：维护版本、渠道、灰度、最低支持版本与安装包，并生成公开下载主页。设计见 [Agent 桌面端](../../harness.md)。

## 生命周期与运维

- 状态：`草稿 → 联调中 → 已上线 → 已停用 → 已下线`。停用时网关返回 503 并保留配置；下线后 `client_id` 不复用。
- **密钥轮换**：`client_secret`、`gateway_secret`、`event_secret` 均支持双密钥并存（默认 7 天重叠期），轮换期间新旧都有效，业务滚动发布后再作废旧密钥。
- 应用详情页可见：实例健康、近 24 小时请求量 / 错误率、能力调用量与配额、事件投递成功率与死信、Token 签发量。
- 模式 C（业务自管）应用在列表中标注迁移期限，到期前 30 天提醒。
