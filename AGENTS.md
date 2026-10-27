# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库性质

这是一个**中台架构设计文档仓库**，根目录同时包含平台代码 KaifangMetaPlatform（后端基于 vue-fastapi-admin 改造的 FastAPI，前端基于 nova-admin），启动方式见 `README.md`。

- `README.md` — 入口：总体拆分摘要 + 文档目录（每个文档的作用见此处，不在本文件重复）+ 控制台代码启动说明
- `sdk/` — 按语言存放并独立发布的平台 SDK：Python `sdk/python/kaifang-meta-sdk/`、Java `sdk/java/kaifang-meta-spring-boot-starter/`、TypeScript `sdk/typescript/kaifang-meta-shell/`；各子项目维护自己的构建配置与版本，通过对应私服供业务系统引用，不把 SDK 源码复制进业务系统仓库
- `app/iam/` — 认证模块（独立 `iam` schema）；`app/domains/` — 控制台后端业务域（用户、授权、审计、账号、事件，使用 `console_authz` schema；数据标注 `annotation` 使用独立 `annotation` schema）；业务组织由各业务系统维护；`app/core/`、`app/models/base.py`、`app/schemas/base.py` — 跨域公共能力；控制台只信任网关签名身份头、按 `sub` 关联本地用户；`app/api/v1/` — 路由聚合入口；`run.py`、`pyproject.toml`、`uv.lock` — 后端入口与本地依赖；`app/worker.py` — kaifang-meta-platform-worker（事件分发）；`web/` — 控制台前端（nova-admin）；`alembic/` — 数据库迁移与 seed；`docker/` — Dockerfile、Compose、镜像依赖清单、入口脚本、APISIX 与 Nginx 配置
- 唯一配置入口是根目录 `.env`（模板 `.env.example`）；一键启动 `sh start-service.sh`；表结构只经 alembic 变更
- `docs/*.md` — 总体与跨部署段设计；`docs/platform/` — 按平台模块拆分（`auth/`、`capability/`、`annotation/`、数据与调度）
- `docs/design/architecture.html` — 系统架构图，纯 HTML/CSS（无 JS），上中下结构：接入端 → [独立进程 | 网关 + 平台模块 | 业务系统] → 平台基础设施，颜色块与带标注箭头表示角色与调用方向
- `docs/design/prototype.html` — 单文件、hash 路由的高保真静态原型（平台控制台 + 智慧档案室），所有数据均为示例数据

## 规范

通用功能开发与 bug 修复流程见 skill [kaifang-meta-development](.agents/skills/kaifang-meta-development/SKILL.md)，涉及 `web/` 界面时同时使用 [kaifang-meta-ui](.agents/skills/kaifang-meta-ui/SKILL.md)；涉及文档、架构图或原型时同时使用 [kaifang-meta-docs](.agents/skills/kaifang-meta-docs/SKILL.md)。新增或调整开发规范时，补充到适用的 skill；没有合适 skill 时新建并在此登记，本文件只保留入口与仓库级约束。

文档结构、一致性同步、命名与写作约定、原型界面约定见 skill [kaifang-meta-docs](.agents/skills/kaifang-meta-docs/SKILL.md)，新增或修改任何文档、架构图、原型前先使用它。

前端（`web/`）的设计语言统一为 nova-admin 风格，新增或修改页面、组件、菜单、权限前先使用 skill [kaifang-meta-ui](.agents/skills/kaifang-meta-ui/SKILL.md)，优先复用 nova-admin 组件。

最重要的一条始终适用：发现文档与实现（或文档之间）不一致时，先停下与用户确认是改文档还是改实现。

## 架构要点（跨文件才能看出的约束）

- 纯 Docker（Compose）多主机部署，不使用 K8s：上游是「主机 IP:端口」静态节点，由平台下发到 APISIX。
- 只拆三个部署段：网关（APISIX，不自研、不引入 Nacos）、平台（模块化单体，六个模块：认证、能力、AI、数据采集、数据标注、任务调度）、业务系统（各自独立部署）。
- 平台基础设施只有 PostgreSQL + pgvector、Redis、MinIO：不引入 RabbitMQ / Temporal / Milvus / EMQX，事件用 outbox + 分发器、调度用 PostgreSQL 任务表、设备走 HTTPS 上报。
- 平台模块间只走接口、每模块独立 schema、不跨模块访问表。kaifang-meta-operator / kaifang-meta-platform-worker / kaifang-meta-edge-agent 是独立进程，不算业务服务。
- 认证模块只维护登录账号、认证凭据、全局唯一 `sub`、账号状态与 SSO；**业务系统维护本地用户资料、组织、角色、菜单和数据权限**，按 `sub` 关联本地用户。已有企业 IdP / LDAP 时优先复用，不复制身份主数据。
- 权限是「一套组件，多份数据」：SDK 统一权限组件（RBAC）由平台控制台（内置应用 `kaifang-meta-console`，数据在 `console_authz`）和业务系统共用，数据各存本系统；不建中心授权服务，Token 不带角色权限。
- 能力是统一目录：算子、流水线、模型、知识库、Agent 都是能力；能力模块是控制面，AI 模块 / 算子节点 / 任务调度是提供方。能力经应用空间下放给业务系统。
- 数据标注是平台模块，不是业务系统：只嵌入从源码构建并汉化的 Label Studio 编辑器做画布（不部署 Label Studio 服务），海量文件默认引用业务存储、由业务签发下载地址，工单、分配、质检、存储自建；支持分配标注（任务池领取 / 指定用户）与自由标注；参与者都是平台身份账号，业务入口打开的工作台按工单成员授权；编辑器中英文由平台设置控制。
- 核心演示流程「导入 → 解析与预抽取 → 送标注 → 标注 → 质检回传 → 回写确认」跨越智慧档案室与中台；幂等键为「批次号 + 档号」，标注期间档案只读。

# UI设计
- 避免不必要的次级标签和描述。让布局本身来说明。
