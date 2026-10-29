# 原型路由

原型：[design/prototype.html](design/prototype.html)，浏览器直接打开，hash 路由。原型数据均为示例数据。

| 区域 | 路由 |
|------|------|
| 入口 | `#login` → `#portal`、`#download`（Agent 桌面端下载主页，无外壳） |
| 平台 · 认证 | `#users`（IAM 身份与控制台成员信息合并展示）、`#orgs`（机构树）、`#tenants`（租户信息）、`#apps`、`#releases`、`#roles` |
| 平台 · 能力 | `#caps` → `#op-ocr`、`#space`、`#kb` → `#kb-detail`、`#agents` → `#agent-detail`、`#models` |
| 平台 · 数据 | `#ingest`、`#label` → `#anno-task` / `#anno-new`、`#anno-mine`、`#anno-tpl` → `#anno-layout`（布局设计器） |
| 平台 · 标注工作台（由业务系统或「我的标注」打开，无侧栏） | 分配标注 `#label-work` → `#label-review`；自由标注 `#label-free`；布局插件演示 `#label-form` |
| 平台 · 网页版 Agent（由门户或业务系统打开，无侧栏） | `#agent-chat` |
| 平台 · 运维 | `#jobs`、`#settings`（平台设置 · 界面语言） |
| 平台 · 运维看板 | 控制台中 MinIO、APISIX、etcd 在内容区新标签页内嵌打开；原型中为新窗口外链，不属于原型 hash 路由 |
| 智慧档案室 | `#ar-home`、`#ar-list` → `#ar-detail`、`#ar-import` → `#ar-batch` → `#ar-send` → `#ar-writeback`、`#ar-label` → `#label-work` / `#label-review`、`#ar-qa`、`#ar-roles` |

导入工作流演示入口：`#ar-import`，页面顶部流程条可在 6 个步骤间跳转。
