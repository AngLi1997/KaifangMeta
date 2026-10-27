# 中台架构设计

kaifang-meta 中台的架构设计文档仓库：文字设计 + 架构图 + 高保真原型，无需构建。

## 总体拆分

| 部署段 | 形态 | 说明 |
|--------|------|------|
| 网关 | APISIX × N（开源，不自研，Docker 部署） | 路由、JWT 校验、身份头注入、限流灰度 |
| 平台 | 模块化单体 kaifang-meta-platform × N | 认证、能力、AI、数据采集、数据标注、任务调度六个模块 |
| 业务系统 | 各自独立部署 | 智慧档案室、文书加工系统、统建系统、库房管理 |
| 客户端 | Agent 桌面端 `kaifang-harness` | 统一认证，本机 Agent 使用平台模型，知识库经平台 MCP，版本在平台发布 |

独立进程：算子节点 `kaifang-meta-operator`、知识库与 Agent 引擎 `kaifang-meta-weknora`（开源 WeKnora）、`kaifang-meta-platform-worker`（PostgreSQL 任务表）、`kaifang-meta-edge-agent`（现场硬件）。平台基础设施只有 PostgreSQL + pgvector、Redis、MinIO 三件。详见 [总体架构](docs/overview.md)。

## 文档目录

| 文档 | 作用 | 主要内容 | 状态 |
|------|------|----------|------|
| **总体与跨部署段** | | | |
| [总体架构](docs/overview.md) | 先读：系统怎么拆、各部分是什么 | 部署段、平台模块、独立进程、基础设施、命名约定 | — |
| [网关与鉴权](docs/gateway.md) | 网关做什么、请求如何被认证 | 三种鉴权模式、Token、身份头签名、轻租户、APISIX 集成 | 已实现 |
| [鉴权流程](docs/auth-flow.md) | 登录到退出的完整时序 | 登录 / SSO、续期、吊销、服务调用、代表用户、401 / 403 语义 | 已实现 |
| [业务与平台通信](docs/communication.md) | 业务系统如何调用平台、平台如何通知业务 | 同步 / 异步通道、接口约定、事件投递、导入 → 回写时序 | 部分实现 |
| [多应用设计](docs/apps.md) | 有哪些应用、应用间如何通信、数据存哪里 | 应用清单、应用 ↔ 平台 / 应用 ↔ 应用通道、数据归属 | 设计中 |
| [对象存储路径](docs/storage.md) | 平台文件存在 MinIO 哪里、新业务如何登记目录 | 单桶、业务目录规则、目录登记表、保留期、访问规则 | 设计中 |
| [多节点部署](docs/deployment.md) | 如何多机部署与发布 | Docker Compose、无状态、共享状态、缓存失效、高可用、降级 | 部分实现 |
| **平台 · 认证** | | | |
| [统一认证与身份](docs/platform/auth/identity.md) | 平台管账号与租户，业务管用户 | 身份账号维护、租户管理、`sub` 关联、轻租户 | 已实现 |
| [应用接入](docs/platform/auth/app-onboarding.md) | 业务系统如何接入平台 | 应用描述 YAML、配置下发、接入流程、生命周期 | 部分实现 |
| [统一权限组件](docs/platform/auth/authz.md) | 菜单 / 按钮 / 数据权限怎么做 | 一套组件多份数据、数据模型、控制台内置角色、防越权 | 部分实现 |
| **平台 · 能力 / AI** | | | |
| [能力目录与下放](docs/platform/capability/catalog.md) | 能力如何登记、授权给业务 | 统一目录、应用空间、四层下放、数据范围、计量配额 | 设计中 |
| [能力点](docs/platform/capability/binding.md) | 代码与平台配置的分工 | 代码声明能力点，平台配置版本 / 参数 / 灰度 | 设计中 |
| [算子](docs/platform/capability/operator.md) | 如何开发和接入一个算子 | 统一算子协议、部署与复用 | 设计中 |
| [知识库与 Agent 版本](docs/platform/capability/knowledge-agent.md) | 知识库 / Agent 如何发布回滚 | 不可变快照、`prod` 别名、评测回归 | 设计中 |
| [知识库与 Agent 引擎（WeKnora）](docs/platform/capability/weknora.md) | 如何用 WeKnora 承载知识库与网页版 Agent | 部署与对象映射、海量档案导入与存储、分区权限、自建界面、与标注的关系 | 设计中 |
| **平台 · 数据与调度** | | | |
| [数据标注](docs/platform/annotation/overview.md) | 标注模块总览 | 模块边界、分配标注（任务池 / 指定用户）与自由标注、平台用户与权限、核心对象、状态机、分期 | 部分实现 |
| [Label Studio 集成与语言](docs/platform/annotation/labelstudio.md) | 编辑器如何构建、嵌入、汉化 | 源码构建、嵌入接口、汉化来源、平台级中英文控制 | 部分实现 |
| [场景模板](docs/platform/annotation/templates.md) | 标注界面如何自定义 | 模板组成、参数与映射、内置场景库、自定义与版本 | 部分实现 |
| [工作台布局与插件](docs/platform/annotation/layout.md) | 标注工作台如何布局与扩展 | 可嵌套布局容器、XML 与拖拽设计器（含 Label Studio 原生标签）、按钮 / 著录表单 / 数据表格组件、JSON / YAML 导出、组件联动 | 部分实现 |
| [工作台组件](docs/platform/annotation/components/README.md) | 工作台组件怎么用 | 工作台、网格、列表、面板、表单、数据表格、按钮栏、按钮、间隔、画布、布局设计器：演示、生命周期、属性、事件、方法；组件分工与去重 | 部分实现 |
| [组件事件与框选回填](docs/platform/annotation/linkage.md) | 工作台组件修改如何传出、画布控件如何回填表单 | 表格 change 事件的三条去路（组件联动 / 宿主消息 / 业务数据源与结果）、Label Studio 控件 bind / pick 回填表单与表格、识别接口、校验与分期 | 设计中 |
| [业务系统对接](docs/platform/annotation/integration.md) | 业务如何嵌入标注与收发数据 | 页面嵌入、海量数据引用模式、清单分片、接口、事件、时序 | 设计中 |
| [数据采集](docs/platform/ingest.md) | 外部数据与现场硬件如何进入平台 | 连接器、原始区、edge-agent 上报与指令 | 设计中 |
| [定时任务与异步处理](docs/platform/scheduler.md) | 长任务、定时任务如何执行 | PG 任务表、Worker、队列并发、重试超时幂等 | 部分实现 |
| **客户端与分发** | | | |
| [Agent 桌面端](docs/harness.md) | `kaifang-harness` 如何使用平台 | 认证、模型、知识库 MCP、版本发布、下载主页 | 设计中 |
| [SDK / Starter](docs/sdk.md) | 业务系统用什么包接入 | 包名、分发渠道、协议与功能 | 设计中 |
| **图与原型** | | | |
| [架构图](docs/design/architecture.html) | 一张图看全局 | 接入端、网关、平台模块、业务系统、基础设施 | — |
| [高保真原型](docs/design/prototype.html) | 界面与交互示意 | 平台控制台 + 智慧档案室，示例数据 | — |
| [原型路由](docs/prototype.md) | 原型页面索引 | hash 路由表 | — |

HTML 浏览器直接打开即可，例如：

```bash
open docs/design/prototype.html#ar-import
```

## KaifangMetaPlatform（平台代码）

仓库根目录是平台进程的代码：后端 FastAPI（Python 3.11+，基于 [vue-fastapi-admin](https://github.com/mizhexiaoxiao/vue-fastapi-admin) 改造），前端以 [nova-admin](https://github.com/chansee97/nova-admin)（MIT，`web/LICENSE-nova-admin`）为基座：Vue 3 + TypeScript + Naive UI + UnoCSS。

| 部分 | 位置 | 说明 |
|------|------|------|
| 认证模块 | `app/iam`（`iam` schema） | 身份账号、全局唯一 `sub`、SSO；OIDC 授权码 + PKCE、Refresh Token 轮换、client credentials（Service Token）、Token Exchange；RS256 + JWKS，密钥可轮换；启动时经 Admin API 下发平台路由 |
| 身份目录 API | `/kaifang-meta/platform/iam/v1/*` | 平台 API（模式 A，scope `directory:read`），支持 `X-KM-On-Behalf-Of` 代表用户 |
| 平台控制台 | `app/`（`console_authz` schema）+ `web/` | 内置应用 `kaifang-meta-console`，只信任网关签名身份头；提供租户和 IAM 身份账号管理，新建身份账号不自动开通控制台成员；租户 / 应用 / 资源授权见 [统一权限组件](docs/platform/auth/authz.md)，业务组织由各业务系统维护 |
| 事件分发 | `python -m app.worker` | `kaifang-meta-platform-worker`：outbox → 按订阅投递，HMAC 签名，失败退避重试与死信；控制台订阅 `user.*` |
| 网关插件 | `docker/apisix/plugins` | `km-identity`：清洗 `X-KM-*`、`aud`、吊销、租户开通、scope / 调用方、代表用户、签名身份头；登录接口与控制台按 应用 × 租户 限流 |

| 项 | 约定 |
|----|------|
| 配置 | 只用根目录 `.env`（模板 `.env.example`），后端、前端、`docker/docker-compose.yml`、启动脚本共用 |
| 数据库 | PostgreSQL + pgvector，库 `kaifang-meta-platform`；`iam`、`console_authz`、`annotation` 三个 schema，仅按 `sub` 关联 |
| 迁移 | alembic（`alembic/versions`，版本表在 `public`）：控制台、身份、seed、应用接入、事件、菜单和审计迁移；`0010` 清理历史控制台成员，`0011` 合并身份账号入口，`0012` 增加租户管理，`0016` / `0017` 增加数据标注（`annotation` schema、菜单与接口） |
| 会话 | SSO 会话、授权码、Refresh Token、吊销键均存 Redis |
| 基础设施 | `docker/docker-compose.yml`：PostgreSQL 5432、Redis 6379、MinIO 9000 / 9001（HTTPS Console 9444、S3 API 9445）、etcd 2379、APISIX 9080 / 9180（HTTPS Dashboard 9181） |
| 镜像构建 | `docker/requirements.txt` 由 `pyproject.toml` / `uv.lock` 导出；从仓库根目录执行 `docker build -f docker/Dockerfile -t kaifang-meta-platform:local .` |
| 端口 | 前端 3001，后端 8080 |
| 前端规范 | 设计语言统一为 nova-admin 风格，优先复用其组件，见 skill [kaifang-meta-ui](.agents/skills/kaifang-meta-ui/SKILL.md) |

### 启动

需要 Docker、[uv](https://docs.astral.sh/uv/)、Node 20+ 与 pnpm。

```bash
sh start-service.sh
```

脚本依次：生成 `.env`（如缺失，并生成各签名密钥）→ 停止上次启动的后端、worker 与前端 → 释放被占用的端口（停止其他容器或进程）→ 启动基础设施并重载网关插件 → 创建 bucket → `alembic upgrade head` → 源码启动后端（启动时下发网关路由）、worker 与前端。运行 `sh stop-service.sh` 可停止这三个进程；基础设施可在仓库根目录执行 `docker compose --project-directory . -f docker/docker-compose.yml down` 停止。

浏览器访问前端 3001：`/kaifang-meta/*` 由 Vite 代理到 APISIX，登录、Token、控制台 API 与生产链路一致。Token 只存内存，到期前 2 分钟自动续期，刷新页面经 `prompt=none` 静默恢复。局域网通过 IP 访问时必须启用 HTTPS（浏览器仅在安全上下文提供 PKCE 所需的 WebCrypto），并在访问设备上信任证书；同时将 `VITE_HTTPS=true`、`IAM_COOKIE_SECURE=true`，将 IP 对应的 HTTPS 回调地址加入 `.env` 中 `CONSOLE_REDIRECT_URIS` 与 `CONSOLE_POST_LOGOUT_REDIRECT_URIS`，重启服务。HTTPS 模式也会启用 MinIO（默认端口 9444）与 APISIX Dashboard（默认端口 9181）的 TLS 反代；APISIX Dashboard 在每台浏览器首次打开时需在 Settings 中填入 `.env` 的 `APISIX_ADMIN_KEY`。

| 地址 | 说明 |
|------|------|
| http://localhost:3001 | 控制台，默认账号 `admin` / `123456`（`.env` 中 `CONSOLE_ADMIN_*`） |
| https://localhost:3001 | 启用 `VITE_HTTPS=true` 后的控制台地址 |
| http://localhost:8080/docs | 后端 API 文档（直连后端没有网关身份头，鉴权接口会返回 401） |
| http://localhost:9080/kaifang-meta/iam/.well-known/openid-configuration | OIDC 发现文档 |
| http://localhost:9001 | MinIO 控制台 |

### 运维命令

注册业务应用（机密客户端，密钥只显示一次）：

```bash
uv run python -m app.iam.cli create-client --client-id kaifang-meta-archive-room --name 智慧档案室 --scopes directory:read,delegate:user
```

轮换签名密钥（新公钥立即进入 JWKS，各节点在 `IAM_KEY_CACHE_TTL` 内切换签名）：

```bash
uv run python -m app.iam.cli rotate-key
```

旧 kid 签发的 Token 全部过期后退役旧密钥：

```bash
uv run python -m app.iam.cli retire-key <kid>
```

### 数据库迁移

```bash
uv run alembic upgrade head
```

```bash
uv run alembic revision -m "说明"
```

表结构由 alembic 管理，ORM（Tortoise）不自动建表；新迁移手写 `upgrade` / `downgrade`。

### 目录

```
├── .env.example           // 统一配置模板
├── docker                  // Dockerfile、Compose、依赖清单、忽略规则、入口脚本、APISIX 与 Nginx 配置
├── start-service.sh       // 一键启动
├── stop-service.sh        // 停止源码进程
├── alembic                // 数据库迁移与 seed
├── app                    // 后端
│   ├── iam                // 认证模块：账号、OIDC、Token、会话、身份目录 API、网关下发、运维命令
│   ├── domains            // 控制台业务域：users、authorization、auditlog、accounts、events、annotation（数据标注，annotation schema）
│   ├── api/v1             // 控制台路由聚合入口
│   ├── core               // 公共 CRUD、网关身份头校验、中间件、Redis
│   ├── models / schemas   // 公共 ORM 基类与响应结构
│   ├── settings           // 配置（读取根目录 .env）
│   └── worker.py          // kaifang-meta-platform-worker：事件分发
└── web                    // 前端（nova-admin，读取根目录 .env）
    └── src
        ├── layouts        // nova 布局（ProLayout、标签栏、面包屑、设置）
        ├── components     // nova 通用组件 + SearchCard
        ├── hooks          // usePageTable、usePermission 等
        ├── service        // alova 请求、OIDC 登录、接口函数
        ├── store          // 鉴权、动态路由（后端菜单 → 路由）、标签、主题
        └── views          // 工作台、个人中心、system/*、annotation/*
```
