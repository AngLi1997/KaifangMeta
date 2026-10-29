# 统一门户

> 平台 · 认证模块，界面由控制台前端 `web/` 承载。相关：[应用接入](app-onboarding.md)、[鉴权流程](../../auth-flow.md)、[统一认证与身份](identity.md)。

## 要点

- 门户是控制台前端里的一个无侧栏页面 `/portal`，登录后默认落地；任何启用的身份账号都能进入，**不要求是控制台成员**。
- 门户只展示当前用户在当前租户下可进入的应用，判定与 `/authorize` 相同（见 [应用接入 · 应用访问判定](app-onboarding.md#应用访问判定)），不按业务组织或业务角色筛选。
- 点击应用整页跳到该应用 `portal.entry`，由应用的前端壳以 `prompt=none` 静默换取本应用 Token，沿用当前租户，不出现登录页。
- 中台控制台本身也是门户里的一个应用磁贴，只对控制台成员显示。
- 门户不做应用内菜单聚合、待办聚合和收藏；这些属于各业务系统。

## 页面

原型 `#portal`。

| 元素 | 行为 |
|------|------|
| 应用磁贴 | `portal.icon` + 名称 + `portal.description`，按 `portal.order`、名称排序；`disabled` 状态灰显“维护中”且不可点 |
| `desktop` 应用 | 进入下载主页 `/kaifang-meta/harness/` |
| 租户切换 | 仅多租户账号显示；选中后以 `tenant=<tid>` 重新授权控制台（SSO 会话内免登录），换到新 `tid` 后回到门户 |
| 用户菜单 | 个人中心、退出（结束 SSO 会话，所有应用退出） |
| 空列表 | “当前租户下暂无可访问的应用，请联系租户管理员” |

## 登录落地

| 场景 | 落地 |
|------|------|
| 打开控制台根地址 / 登录页登录 | `/portal` |
| 从某个应用发起登录 | 回到该应用（各应用的回调地址），不经门户 |
| 控制台成员点“中台控制台” | 控制台首页（现有带侧栏布局） |
| 非成员直接访问控制台其他路由 | 重定向 `/portal` |

## 接口

门户使用控制台的 Access Token（`aud=kaifang-meta-console`），走现有 `km-console` 路由；接口只校验网关身份，不校验控制台成员与角色。

```http
GET /kaifang-meta/console/api/v1/portal/apps
```

```json
{
  "code": 200,
  "data": {
    "tenant": { "id": "t_5e2a9c1d7b3f4086", "name": "省档案馆" },
    "tenants": [{ "id": "t_5e2a9c1d7b3f4086", "name": "省档案馆" }, { "id": "t_43f12ac77e108d2b", "name": "市档案馆" }],
    "apps": [
      { "client_id": "kaifang-meta-console", "name": "中台控制台", "icon": "KM", "description": "用户 · 能力 · 采集 · 调度", "entry": "/", "status": "online" },
      { "client_id": "kaifang-meta-archive-room", "name": "智慧档案室", "icon": "档", "description": "著录 · 检索 · 问答", "entry": "https://archive.internal/", "status": "online" }
    ]
  }
}
```

- 控制台接口层调用认证模块的 `list_accessible_apps(sub, tid)`（模块接口，不直接读 `iam` 表），再按 `console_authz.user` 是否存在决定是否加入控制台磁贴。
- 列表只含登记了 `portal.entry` 的应用，纯后端服务不显示；状态判定落地后只含 `online` 与 `disabled` 应用，`testing` 应用只对成员名单内的用户显示并带“联调中”标记。

## 实现状态

| 项 | 状态 |
|----|------|
| 原型 `#portal` | 已绘制 |
| `/portal` 页面、`GET /portal/apps`、登录默认落地、非成员重定向、门户内直接切换租户（`/authorize?tenant=`） | 已实现 |
| `iam.client.portal`（迁移 `0020`）；业务应用经 CLI `create-client --portal-entry --portal-icon --portal-description` 登记 | 已实现 |
| `disabled` 应用灰显「维护中」且不可点 | 已实现 |
| 可见判定中的成员名单、`testing` 状态 | 设计中 |
