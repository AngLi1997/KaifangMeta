# prototype.html 结构

单文件、hash 路由的高保真静态原型（平台控制台 + 智慧档案室），所有数据均为示例数据。单个 `<script>` 内完成全部渲染：

- `pages` 对象：路由名 → 返回 HTML 字符串的函数。新增页面需同时加 `pages[route]` 和 `CRUMB[route]`（面包屑），并更新 `docs/prototype.md` 路由表。
- 路由前缀决定外壳：`ar-` 开头渲染为智慧档案室（`ARCHIVE_NAV`，主色 `--ar-accent`），其余为平台控制台（`PLATFORM_NAV`，主色 `--accent`）；`login`、`portal` 不套外壳。未知路由回落到 `login`。
- 详情 / 子页面通过 `PARENT` 映射到侧栏高亮项；跨系统工作流步骤条由 `FLOW` 数组定义，用 `flow(route)` 渲染。
- 小模板助手：`T`（表格）、`S`（标签）、`D`（带点状态）、`P`（进度条）、`card`、`ph`（页头）。优先复用，不新写同类助手。
- 颜色全部用 `:root` CSS 变量，深色模式在 `@media (prefers-color-scheme: dark)` 中重定义；新增颜色需两处都加。
- 字体经 Google Fonts 引入（Noto Sans SC、IBM Plex Mono），其余全部内联，保持单文件无外部依赖。
