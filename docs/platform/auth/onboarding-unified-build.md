# 统建系统接入

> 平台 · 认证模块，首个存量业务系统接入方案（分支 `dev-meta-light`，涉及平台仓库与 `archive-platform-backend` / `archive-platform-frontend`）。相关：[应用接入](app-onboarding.md)、[统一门户](portal.md)、[网关与鉴权](../../gateway.md)、[鉴权流程](../../auth-flow.md)、[SDK](../../sdk.md)。

## 要点

- **目标只有三条**：门户能看到统建系统；点击整页进入、不出现登录页；统建会话失效时回到平台登录页，登录后回到原页面。
- **用户与机构在平台维护，角色归统建**：身份账号、机构树、账号所属机构由平台「身份账号」「机构管理」维护，统建经身份目录 API 读取（不读平台或底座数据库）；统建本地角色表、用户—角色绑定、菜单、数据范围仍在统建维护。
- **不换业务数据**：统建的 PostgreSQL（`common` / `audit` / `prefiling` 等）、MinIO、Redis、RabbitMQ 保持原样，不迁到平台。
- **平台新增「机构管理」**：按租户维护机构树（编码、名称、上级、排序、状态），身份账号增加所属机构；底座机构一次性导入并保留原 ID 与编码，统建已存的机构 ID、登记机关编码不用迁移。
- **先做平台「应用接入」**：数据表格管理已接入应用，注册 / 编辑 / 上线停用后经 APISIX Admin API 下发路由与上游（etcd 是 APISIX 的派生存储，平台不直接写 etcd），表格显示网关下发状态与上游实例健康。
- **Java starter 只做身份**：`kaifang-meta-spring-boot-starter` 首版提供网关签名身份头校验、`KmContext`、按 `sub` 查身份目录；事件、RBAC、能力调用后续再加。
- **统建后端加一层适配**：starter 校验出 `sub` 后，查统建本地用户（首次访问自动建档、不授角色）与其本地角色，构造原有 `VerifiedIdentity`，下游 `AccessPolicy`、会话授权缓存、服务间内部签名调用都不改。
- **统建前端只换 Token 来源**：从读底座 `Admin-Token` Cookie 改为 OIDC 授权码 + PKCE（Token 只在内存），API 基址改为平台网关前缀，401 时续期失败就跳平台登录。

## 现状对照

| 项 | 统建现状（数据底座） | 接入平台后 |
|----|----------------------|------------|
| 登录 | 底座登录页，Token 写同源 Cookie `Admin-Token` | 平台登录页，OIDC 授权码 + PKCE，Token 只存内存 |
| 网关 | 底座网关 `/gateway-api` → `/platform-common`（9081）、`/prefiling`（9082） | APISIX `/kaifang-meta/ub/platform-common/*`、`/kaifang-meta/ub/prefiling/*`，去前缀后转发到原服务 |
| 身份头 | `X-User-Id / X-User-Name / X-Dept-Id / X-Session-Id` + `X-Internal-Token`（HMAC），角色在不签名的 `X-User-Roles` | `X-KM-User-Id`（`sub`）/ `X-KM-Tenant-Id` / `X-KM-Client-Id` / `X-KM-Ts` / `X-KM-Sign`，不带角色 |
| 用户 | 底座 `admin.sys_user` | 平台身份账号（含所属机构）；统建 `common.app_user` 存本地副本（`sub` 唯一） |
| 角色 / 用户角色 | 底座 `admin.sys_role` / `sys_user_role`，统建经底座接口读取 | 统建 `common.app_role` / `common.app_user_role`，统建页面维护 |
| 机构 | 底座 `admin.sys_dept`，经底座接口读取 | 平台 `iam.org`，统建经身份目录 API 读取 |
| 菜单与权限 | 统建 `common.permission_role_menu` 等，按 `roleIds` 查 | 不变，`sys_role_id` 改为指向 `common.app_role.id` |
| 服务间调用 | 预归档 → 公共服务用 `INTERNAL_TOKEN_SECRET` 重新签名 | 不变 |
| 会话失效 | 提示后跳底座 `/home?relogin=1` | 先静默续期，失败跳平台 `/authorize`（登录页），登录后回原页面 |
| 数据库 / MinIO / Redis | 统建自有 | 不变，不迁到平台 |

## 目标链路

```text
浏览器                平台控制台(门户)          APISIX                      统建前端 / 后端
  │ 登录 ─────────────▶ /kaifang-meta/iam/login（SSO Cookie）
  │ 门户 ─────────────▶ GET /portal/apps → 统建磁贴（portal.entry）
  │ 点击磁贴 ─────────────────────────────────────────────────────────────▶ 统建前端 /archive/
  │ 统建前端 shell：/authorize?prompt=none（平台源，SSO 免登录）→ 回调统建根地址 /?code= → 换 Token
  │ API：Bearer ──────────────────────────────▶ /kaifang-meta/ub/platform-common/session/access
  │                                          openid-connect 验 JWKS → km-identity 签身份头
  │                                          → proxy-rewrite 去 /kaifang-meta/ub ─────▶ 9081 /platform-common/...
  │                                                                       starter 验签 → sub → common.app_user / user_role
  │ Token 过期：refresh_token 续期；Refresh 也失效 → /authorize（无会话即平台登录页）→ 登录后回原页面
```

## 平台：机构管理

控制台菜单「认证 / 机构管理」，原型 `#orgs`。机构是身份主数据的一部分，与身份账号一样按租户隔离，设计见 [统一认证与身份](identity.md#机构)。

### 存储（alembic）

| 表 / 字段 | 内容 |
|-----------|------|
| `iam.org` | `id`（bigint，序列）、`tenant_id`、`parent_id`（根为空）、`code`（租户内唯一）、`name`、`sort_order`、`status`（`active` / `disabled`）、`created_at`、`updated_at` |
| `iam.account.org_id` | 账号所属机构（可空，一个账号一个机构），须属于账号的主租户 |

层级不存字段，按 `parent_id` 计算深度（根为 1）。

### 页面

| 区域 | 内容 |
|------|------|
| 机构树表格 | 名称、编码、排序、状态、账号数、创建时间；搜索名称 / 编码；默认展开两级 |
| 操作 | 新增下级、编辑、启用 / 停用、删除；工具栏「新增机构」「导入」 |
| 身份账号 | 新建 / 编辑表单增加「所属机构」（树选择，只列启用机构）；列表增加机构列与按机构筛选 |

- 改上级时拒绝移到自身或后代下。
- 停用机构不影响账号登录，只在选择器中隐藏；删除仅限已停用、无下级、无账号的机构。
- 租户管理员只维护本租户机构；系统租户可切换租户查看。

### 控制台接口

前缀 `/kaifang-meta/console/api/v1/org`，按钮权限码同路径：

| 接口 | 说明 |
|------|------|
| `GET /tree` | 当前租户机构树（含账号数） |
| `POST /create`、`POST /update` | 新增、编辑（编码租户内唯一） |
| `POST /status` | 启用 / 停用 |
| `DELETE /delete?id=` | 删除 |
| `POST /import` | 导入 JSON 列表 `[{id, parent_id, code, name, sort_order, status}]`，保留 `id`，导入后把序列调到最大值之后；同一 `id` 重复导入则更新 |

### 身份目录 API

经现有平台路由 `/kaifang-meta/platform/iam/v1/*`（scope `directory:read`），只返回当前租户数据：

```http
GET /kaifang-meta/platform/iam/v1/orgs
```

```json
{
  "data": [
    { "id": 100, "parent_id": null, "code": "37", "name": "山东省", "level": 1, "sort_order": 0, "status": "active" },
    { "id": 104, "parent_id": 100, "code": "3701", "name": "济南市", "level": 2, "sort_order": 10, "status": "active" }
  ]
}
```

- 账号接口 `GET /accounts/{sub}`、`GET /accounts?username=` 的返回增加 `org_id`。
- 机构增删改写入 outbox `org.changed`（只带 `tenant_id`、`org_id`），账号换机构写 `user.updated`；首版统建按 TTL 缓存，不订阅事件。

### 从底座导入

运维从底座导出启用与停用的机构（`dept_id → id`、`parent_id`、`dept_name → name`、`code`、`order_num → sort_order`、`status`），在「机构管理」导入。账号按登录名在平台新建并选择所属机构（底座账号密码不迁移）。

## 平台：应用接入（先做）

控制台菜单「认证 / 应用接入」，原型 `#apps`，按 [应用接入](app-onboarding.md) 的设计取首版子集。

### 数据表格

| 列 | 来源 |
|----|------|
| 应用 | `name`，可点开详情抽屉 |
| `client_id` | `iam.client.client_id` |
| 类型 | `web` / `service` |
| 鉴权模式 | 首版只有 `gateway`（网关托管） |
| 开通租户 | `tenants`，多于 1 个显示 `+N` |
| 网关前缀 | `gateway.prefix` |
| 网关 | 下发状态：已下发 / 待下发 / 配置漂移 / 未配置 |
| 实例 | 上游健康节点数 / 总数 |
| 状态 | 已上线 / 已停用 |
| 操作 | 编辑、上线 / 停用、重新下发、轮换密钥 |

工具栏：搜索（名称 / `client_id`）、注册应用。注册成功后弹窗一次性显示 `client_secret`、`gateway_secret`，关闭后不可再看。

### 编辑表单（抽屉，按段）

| 段 | 字段 |
|----|------|
| 基本 | 名称、`client_id`（创建后只读）、类型、负责人 |
| 登录 | 回调地址、退出回调地址（多值） |
| 网关 | 前缀；路由列表（子路径 → 上游节点 `IP:端口` 多值、是否去前缀）；健康检查路径；公开路径 |
| 开通 | 租户（多选） |
| 门户 | 图标、描述、入口地址、排序 |

统建系统一个应用多条路由（公共服务、预归档两套上游），所以 `gateway.routes` 是列表，与 [应用接入 · 应用描述](app-onboarding.md#接入对象应用描述) 的单 `upstream` 写法不同，需同步更新该文档。

### 存储变更（alembic）

- `iam.client` 增加 `gateway`（JSONB：`prefix`、`routes[]`、`health_check`、`public_paths`）、`owner`、`sync_status`、`synced_at`。
- `status` 取值从 `active` / 其他 改为 `online` / `disabled`，迁移把 `active` 改为 `online`，同步修改认证模块中按 `status="active"` 判定的查询；`testing` / `retired` 与成员名单留到下一版。
- `gateway_secret` 首版存 `iam.client.gateway_secret`（明文，网关 HMAC 需要），不进日志、列表与导出；`iam.client_secret` 多版本表留到做双密钥轮换时再建。

### 控制台接口

前缀 `/kaifang-meta/console/api/v1/app`，按钮权限码同路径，仅系统租户的超级管理员可用：

| 接口 | 说明 |
|------|------|
| `GET /list` | 分页列表，含网关状态与实例健康 |
| `GET /get?client_id=` | 详情，不含密钥 |
| `POST /create` | 注册并下发，响应一次性含 `client_secret`、`gateway_secret` |
| `POST /update` | 更新并重新下发 |
| `POST /status` | `online` / `disabled`；停用时路由改为 `fault-injection` 直接返回 503（需加入 `docker/apisix/config.yaml` 插件列表），授权页拒绝该应用 |
| `POST /sync` | 重新下发 |
| `POST /secret/rotate` | `kind=client` / `gateway`，新密钥只显示一次；首版不做重叠期，轮换 `gateway` 后业务需同步改配置并重启 |

CLI `create-client` 保留，改为复用同一服务函数。

### APISIX 与 etcd

- 平台只调用 APISIX Admin API（`APISIX_ADMIN_URL` + `APISIX_ADMIN_KEY`）；APISIX 把配置写入 etcd（`/apisix` 前缀，Compose 数据卷 `etcd-data` 持久化），APISIX 重启后从 etcd 恢复，不依赖平台重新下发。
- 每个应用的资源 ID 固定，PUT 幂等：

| 资源 | ID | 内容 |
|------|----|------|
| 上游 | `upstreams/km-app-<client_id>-<n>` | `roundrobin` 节点、主动健康检查（`health_check.path`） |
| 路由 | `routes/km-app-<client_id>-<n>` | `uri = <prefix><子路径>/*`；插件 `openid-connect` + `km-identity`（`aud = client_id`、`secret = gateway_secret`、`tenants`）+ `proxy-rewrite`（去前缀）+ 按租户 `limit-count` |
| 公开路由 | `routes/km-app-<client_id>-<n>-public` | 公开路径，只有 `proxy-rewrite`，`priority` 高于鉴权路由 |

- 已删除的子路由按 ID 前缀 `km-app-<client_id>-` 比对后删除，避免残留。
- **网关状态**：保存后同步下发，成功记 `已下发` + `synced_at`；失败照常保存并记 `待下发`。列表打开时 `GET /apisix/admin/routes` 比对期望配置，不一致显示 `配置漂移`，可点「重新下发」以平台为准覆盖。定时对账留到下一版。
- **实例健康**：列表打开时平台直接探测各上游节点的 `health_check.path`（超时 2 秒，结果缓存 30 秒）；APISIX Control API 只监听容器内 127.0.0.1，平台访问不到，不使用。未配置健康检查时显示 `—`。
- 平台启动时已有的 `sync_platform_routes()` 增加：重新下发全部 `online` 应用。

### 门户

现有 `accessible_apps()` 已按「应用启用 ∧ 租户已开通 ∧ 有 `portal.entry`」显示磁贴，只需把启用判定改为 `status == "online"`；`disabled` 磁贴灰显「维护中」按 [统一门户](portal.md) 处理。

## Java starter

源码 `sdk/java/kaifang-meta-spring-boot-starter/`（Maven，Java 17，Spring Boot 3.5，与统建一致）。首版只含：

| 能力 | 说明 |
|------|------|
| `KmIdentityFilter` | 校验 `X-KM-*` 与 `X-KM-Sign`：签名串 `method + path(?query) + ts + user + tenant + client + on_behalf_of`，HMAC-SHA256，时间窗 ±5 分钟；`path` 为**网关外部路径**，即 `gateway-prefix + 请求 URI`（APISIX 在去前缀之前签名）；无身份头的请求不处理，交给后续过滤器 |
| `KmContext` | 请求级 `sub`、`tid`、`client_id`、`principal_type`、`request_id` |
| `KmDirectory` | `client_credentials` 换 Service Token（缓存到期前续期）；`account(sub)`、`accountByUsername(name)` 取登录名、姓名、`org_id`，`orgs()` 取当前租户机构列表；结果本地缓存（账号 60 秒、机构 5 分钟） |
| `KmPrincipalResolver` | 扩展点：业务实现 `KmContext → Authentication`，starter 写入 Spring Security 上下文；返回空则不认证，由业务认证入口返回 401 |
| 配置校验 | 启用时 `issuer`、`client-id`、`gateway-secret` 不能为空或默认值 |

```yaml
kaifang-meta:
  enabled: ${KM_ENABLED:false}
  issuer: ${KM_ISSUER:http://10.20.0.14:9080/kaifang-meta/iam}
  client-id: kaifang-meta-unified-build
  client-secret: ${KM_CLIENT_SECRET:}
  gateway-secret: ${KM_GATEWAY_SECRET:}
  gateway-prefix: /kaifang-meta/ub
```

分发：先 `mvn install` 到本机，联调稳定后发布 Maven 私服；统建通过 `archive-platform-bom` 管理版本，在 `archive-common-security` 引入。

## 统建后端改造

### 本地用户与角色（Flyway `common` 追加 `V7`）

| 表 | 字段 | 说明 |
|----|------|------|
| `common.app_user` | `id`（bigint，序列从 `100000` 起）、`sub`（唯一）、`username`、`name`、`org_id`、`status`、`created_at`、`updated_at` | `id` 即原 `userId`，用于审计归属；从 `100000` 起避免与历史审计中的底座用户 ID 混淆 |
| `common.app_role` | `id`、`role_key`（唯一）、`name`、`sort_order`、`status`（`0` 正常 / `1` 停用，沿用底座编码）、创建与更新人 | `id = 1` 固定为系统管理员（代码中 `PLATFORM_ADMIN_ROLE_ID = 1` 不改） |
| `common.app_user_role` | `user_id × role_id` 主键、`created_by`、`created_at` | — |

- 迁移为现有授权表（`permission_role_menu`、`permission_role_data_scope`）中出现过的每个 `sys_role_id` 补一行 `common.app_role`（名称「角色 <id>」，管理员后续改名），已配置的菜单与数据范围继续有效；不读取底座表。
- 首个管理员：配置 `KM_BOOTSTRAP_ADMINS`（平台登录名，逗号分隔），对应用户首次建档时授予角色 1；之后在统建页面维护。

### 身份适配

| 项 | 做法 |
|----|------|
| 依赖 | `archive-common-security` 引入 starter；`KM_ENABLED=false` 时行为与现在完全一致 |
| 建档 | 公共服务 `LocalUserServiceImpl`（实现 `LocalUserResolver`）：按 `sub` 查 `common.app_user`；不存在时用 `KmDirectory` 取登录名、姓名、`org_id` 建档，**不授予角色**；已存在时这些字段变化则更新，平台不可达时沿用本地副本 |
| 预归档 | 不持有用户表：`CommonLocalUserClient` 调公共服务 `GET /platform-common/internal/local-user/resolve`（内部服务签名 `X-Service-Token`，与网关签名分域），按 `sub + 租户` 缓存 30 秒 |
| 构造身份 | `archive-common-security` 的 `KmPrincipalAdapter`：`new VerifiedIdentity(app_user.id, username, deptId = org_id（无机构为空）, sessionId = "km:" + sub + ":" + tid, [], 启用角色 ID)` |
| 过滤器顺序 | `KmIdentityFilter` 在 `GatewayIdentityFilter` 之前；带 `X-KM-Sign` 走平台身份，带 `X-Internal-Token` 仍走原 HMAC（服务间调用不变） |
| 无角色 / 停用 | 本地用户停用时不生效任何角色；无角色 → `/session/access` 返回空菜单，前端显示「待分配权限」 |
| 会话授权 | `/session/initialize`、`/session/access`、Redis 键、`AccessPolicy` 不改 |
| 公开路径 | 健康检查、OpenAPI 已在 `shouldNotFilter` 中排除，登记为应用公开路径 |
| 配置 | 各服务 `application.yml` 增加上面的 `kaifang-meta.*`，`.env.example` 增加 `KM_ENABLED`、`KM_CLIENT_SECRET`、`KM_GATEWAY_SECRET`、`KM_BOOTSTRAP_ADMINS` |

### 角色与用户接口（公共服务）

| 现有 | 改为 |
|------|------|
| `MetaRoleService`（经底座 Bearer 读角色） | 新实现 `LocalRoleServiceImpl` 读 `common.app_role`，接口签名不变，`PermissionConfigurationServiceImpl`、`PermissionDataScopeServiceImpl` 不改 |
| 底座 `role.deleted` 事件消费 `RoleDeletedStreamConsumer` | 统建删除本地角色时直接调用现有 `DeletedRolePermissionService` 清理授权；`KM_ENABLED=true` 时关闭事件消费（`ROLE_DELETION_STREAM_ENABLED=false`） |

新增接口，前缀 `/platform-common`，按对应按钮权限放行（接口文档见统建后端 `docs/kaifang-meta-integration.md`）：

| 接口 | 说明 |
|------|------|
| `POST /role/save`、`POST /role/delete` | 角色维护（列表沿用 `GET /permission/roles/page`）；角色 1 不能停用或删除 |
| `GET /user/page` | 本地用户列表（登录名、姓名、角色、状态） |
| `POST /user/add` | 按平台登录名预建：经 `KmDirectory` 查 `sub` 后建档 |
| `POST /user/roles` | 设置用户角色（整体替换）；不能移除自己的系统管理员角色 |
| `POST /user/status` | 启用 / 停用本地用户（不影响平台账号） |

按钮权限码随 `V7` 写入 `common.menu`，并默认授予角色 1。

### 机构改读平台

| 现有 | 改为 |
|------|------|
| `MetaDepartmentNameGateway`（`DepartmentNameGateway` 实现，底座内部签名接口） | `KmDepartmentGateway`：用 `KmDirectory.orgs()` 实现 `catalogDirectory()`（`id → deptId`、`parent_id`、`level`、`code`、`name`）、`thirdLevelNames()`、`names(codes)`、`codesByIds(ids)`，机构树、登记机关、采集数据范围不改 |
| `MetaDepartmentServiceImpl`（`MetaDeptHttpApi`，底座 Bearer） | `KmDepartmentServiceImpl`：同样读 `KmDirectory.orgs()`，返回数据范围选项 |
| `MetaRoleHttpApi` | 由 `LocalRoleServiceImpl` 替代 |

`KM_ENABLED=true` 时以上底座客户端都不装配；`MetaSyncClient`（预归档按业务 ID 重采，底座内部签名）与身份无关，保留。

## 统建前端改造

| 项 | 做法 |
|----|------|
| 登录 | 新增 `src/domain/km-auth.js`（取自控制台 `web/src/service/auth/oidc.ts`，后续抽成 `kaifang-meta-shell`）：`main.js` 挂载前调用 `ready()`，处理授权回调或 `prompt=none` 静默授权；统建是 hash 路由，回调地址为应用根地址（`?code=` 在 hash 之前），换完 Token 后恢复原 hash |
| Token | `session.js` 新增 `currentToken()`：启用平台时取内存 Token，否则仍读底座 Cookie；`currentMetaToken()` 及各业务客户端不变 |
| API 基址 | `VITE_GATEWAY_API_BASE=/kaifang-meta/ub`，请求路径 `/platform-common/...`、`/prefiling/...` 不变 |
| 401 | 会话状态变为 401 时先 `refresh_token` 续期并重新加载授权；失败则显示「登录状态已失效」，点「重新登录」发起授权（SSO 会话已失效时即平台登录页），登录后回到当前页面 |
| 重新登录按钮 | 现有「回到底座重新登录」改为跳平台登录，`VITE_META_PLATFORM_URL` 改为平台门户地址 |
| 退出 | 跳平台 `/logout`，结束 SSO 会话，所有应用退出 |
| 角色管理 | 权限配置页 `PermissionConfig.vue` 的角色列表增加新建、编辑、删除 |
| 用户管理 | 新增「用户管理」页：本地用户表格（登录名、姓名、机构、角色、状态）、按平台登录名添加、设置角色、启用 / 停用；账号与机构只读，修改到平台；菜单挂在系统管理下 |

**SSO Cookie 的源**：控制台的 SSO Cookie 设在控制台所在源的 `/kaifang-meta/iam` 路径下。统建前端若部署在不同源，`/authorize` 必须整页跳到**平台源**（`VITE_KM_IAM_URL`，如 `http://10.20.0.14:3001/kaifang-meta/iam`），才能复用门户的登录会话；`/token` 走统建源的反向代理 `/kaifang-meta/*` → APISIX，避免跨域。

## 部署与登记

| 项 | 值（示例） |
|----|------------|
| `client_id` | `kaifang-meta-unified-build` |
| 回调地址 | `http://10.20.0.21:5173/archive/`（应用根地址） |
| 退出回调 | `http://10.20.0.21:5173/archive/` |
| 网关前缀 | `/kaifang-meta/ub` |
| 路由 | `/platform-common` → `10.20.0.21:9081`；`/prefiling` → `10.20.0.21:9082` |
| 健康检查 | `/platform-common/actuator/health` |
| 开通租户 | 统建所在租户（单租户时为系统租户） |
| 门户 | 图标 `统`，描述 `数据接收 · 四性检测 · 预归档`，入口 `http://10.20.0.21:5173/archive/` |
| 首个管理员 | `KM_BOOTSTRAP_ADMINS=admin`（平台登录名） |
| 机构 | 从底座导入到统建所在租户，见「从底座导入」 |

## 验收

1. 平台「机构管理」导入底座机构，树与底座一致；新建账号可选所属机构。
2. 平台「应用接入」注册统建系统，表格显示「已下发」，实例 2 / 2；APISIX Dashboard 与 etcd Workbench 中能看到 `km-app-kaifang-meta-unified-build-*`。
3. 重启 APISIX 容器后路由仍在。
4. 用 `KM_BOOTSTRAP_ADMINS` 中的账号登录平台，门户出现统建磁贴；点击进入统建，不出现登录页，`common.app_user` 新增一行并拥有角色 1。
5. 管理员在统建新建角色、配置菜单，给另一个平台账号（首次访问后自动出现在用户管理，或按登录名预建）分配该角色；该账号刷新后看到对应菜单，未分配角色时显示「待分配权限」。
6. 统建中直接带过期 Token 调接口：静默续期成功；在平台退出后刷新统建页面：跳平台登录页，登录后回到原页面。
7. 停用应用：门户灰显「维护中」，统建接口经网关返回 503。
8. 统建数据范围配置页、机构树、登记机关显示平台机构；平台改机构名后 5 分钟内统建可见。
9. `KM_ENABLED=false` 时统建经底座网关原链路照常可用。

## 实施顺序

| 步 | 仓库 | 内容 |
|----|------|------|
| 1 | 平台 | 机构：迁移、控制台接口与页面、身份账号所属机构、身份目录 `orgs`、导入；原型 `#orgs` |
| 2 | 平台 | 应用接入：迁移、接口、APISIX 下发与状态、控制台页面与菜单 |
| 3 | 平台 | `kaifang-meta-spring-boot-starter` 首版与单元测试 |
| 4 | 统建后端 | `V7` 本地用户与角色、引入 starter、身份适配、角色与用户接口、机构改读平台、配置 |
| 5 | 统建前端 | OIDC 登录、Token 来源、401 处理、重新登录与退出、角色管理、用户管理 |
| 6 | 两边 | 登记应用、按「验收」逐条联调，更新 [应用接入](app-onboarding.md)、[统一门户](portal.md)、[统一认证与身份](identity.md)、[SDK](../../sdk.md) 的实现状态 |

## 实现状态

| 项 | 状态 |
|----|------|
| 平台机构管理（迁移 `0021`、控制台页面与接口、账号所属机构、身份目录 `orgs`、导入） | 已实现，浏览器验证 |
| 平台应用接入（迁移 `0022`、数据表格、注册 / 编辑 / 上线停用 / 重新下发 / 轮换密钥、APISIX 下发与 etcd 持久化、漂移检测、实例探测、门户维护中） | 已实现，浏览器验证 |
| `kaifang-meta-spring-boot-starter` 0.1.0-SNAPSHOT | 已实现，签名校验单元测试通过；与真实 APISIX 签名比对一致 |
| 统建前端（平台登录、续期、重新登录、角色维护、用户管理、静态演示） | 已实现，`npm test` 通过；门户进入免登录、退出后回到平台登录页已验证 |
| 统建后端（`V7`、本地用户与角色、身份适配、机构改读平台） | 已编码；`archive-common-*` 编译通过，公共服务与预归档依赖私服 `kd-archive-flow-spring-boot-starter`，本机无凭据未能编译与联调 |
| 原型 `#orgs` | 已绘制 |

## 待确认

| 问题 | 建议 |
|------|------|
| 底座账号是否需要批量导入到平台（密码不迁移，需管理员重置或首次登录改密） | 统建当前账号少，首版在平台手工新建；需要时再加账号导入 |
| 接入后是否仍保留底座登录入口并行 | 保留，用 `KM_ENABLED` 与前端构建变量切换，不同时开启 |
