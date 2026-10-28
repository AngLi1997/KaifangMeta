---
name: kaifang-meta-ui
description: KaifangMeta 前端（web/，基于 nova-admin）的 UI 开发规范：设计语言统一为 nova-admin 风格，优先复用 nova-admin 已有的布局、组件、hooks、指令，列表页 / 弹窗 / 抽屉 / 树表的标准写法，按钮权限码，图标与配色约定，新增页面与菜单的流程。只要在 web/ 下新增或修改页面、组件、样式、路由、菜单、权限，或为原型 / 新功能设计界面，都应先使用本 skill，即使用户没有明确提到“UI 规范”或 nova-admin。
---

# KaifangMeta UI 开发规范

前端 `web/` 以 [nova-admin](https://github.com/chansee97/nova-admin)（MIT，见 `web/LICENSE-nova-admin`）为基座：Vue 3 + TypeScript + Vite + Naive UI + UnoCSS + alova + pro-naive-ui（布局）。**所有界面的风格与设计语言统一为 nova-admin 风格**；新代码要让人看不出“哪页是后加的”。

## 要点

- **先复用，再新写**。按顺序找：本仓库已有的 nova 组件 / hooks / 指令（清单见 [references/components.md](references/components.md)）→ Naive UI 组件 → 实在没有才新写，且可复用的放 `src/components/common/`。
- **列表页顶部必须有筛选条面板**：使用 `SearchCard` 放置与业务常用查询相关的筛选项，保持字段精简、布局清楚，不为凑形式堆入低频或无用条件；随后是 `n-card`（header 放主操作按钮）+ `DataTable`。新增 / 编辑用 `components/XxxModal.vue`，次级配置用抽屉。模板见 [references/page-templates.md](references/page-templates.md)。
- **对话框、确认框、消息框只用统一封装**：`FormModal`、`confirmDialog`、`message`，保证样式与行为一致；需要新形态时扩展封装，不在页面里直接用 `n-modal` / `window.$dialog` / `window.$message`。
- **强调色跟随主题**：所有用于强调、选中或主操作的组件颜色都必须动态使用当前主题主色（`var(--primary-color)`、`var(--primary-color-hover)` 等，主题在 `src/store/app/theme.json`，用户可在设置抽屉切换）；Naive UI 组件优先使用 `type="primary"`，有颜色属性时传入对应主题变量，不依赖固定默认色。状态颜色继续表达成功、警告、错误等语义。
- **不硬编码颜色、不自造样式**：颜色用 Naive 主题变量，间距与布局用 UnoCSS 工具类和 nova 的 shortcuts（`wh-full`、`flex-center` 等）。
- **图标只用 icon-park-outline**：模板里写组件 `<icon-park-outline-add-one />`（unplugin-icons 自动导入），数据里（菜单、`NovaIcon`）写字符串 `icon-park-outline:add-one`。
- **按钮权限用接口权限码**：`v-permission="'post/api/v1/user/create'"` 或 `hasPermission(...)`，码 = 小写方法 + 去掉网关前缀的接口路径；超级管理员全通过。
- **避免不必要的次级标签和描述，让布局本身说明**（仓库 AGENTS.md 的 UI 约定）：不加“说明：……”段落、不给显而易见的字段写提示；必要的风险提示放进 `NPopconfirm` 文案或 `HelpInfo`。
- **认证与请求不另起炉灶**：一律用 `src/service` 的 alova 实例与 OIDC 函数；Token 只在内存，禁止写 localStorage；不要直接 `fetch` 控制台接口。

## 设计语言（nova-admin 风格）

| 维度 | 约定 |
|------|------|
| 布局 | `ProLayout`（侧边 / 顶部 / 混合由用户在设置中切换）+ 标签栏 + 面包屑，页面只写内容区 |
| 容器 | 内容放 `n-card`；纵向堆叠用 `<n-space vertical>`（默认间距），左右分栏用 `n-flex`，左侧固定宽度 `w-60 shrink-0` |
| 按钮 | 主操作 `type="primary"` 带图标放卡片 header；行内操作 `size="small"`；危险操作 `type="error"` + `NPopconfirm` |
| 表格 | 使用 `DataTable` 填满卡片剩余高度，分页栏贴底、空数据展示空态；单元格不换行，每列按字段可能的最大长度设宽（见 [components.md](references/components.md)「表格列宽」），`DataTable` 按列宽之和自动横向滚动，不手写 `:scroll-x`；操作列设 `fixed: 'right'`，操作按钮使用 `text` 链接样式（“更多”面板内同样使用）；状态用 `NTag size="small"`，开关用 `NSwitch size="small"` |
| 表单 | 查询区 `inline` + `label-placement="left"`；弹窗表单 `label-placement="left"`、`n-grid :cols="2" :x-gap="18"` + `n-form-item-gi` |
| 弹窗 | 表单弹窗一律用 `FormModal`（`v-model:show`、`title`、`size="sm/md/lg"` 对应 480 / 560 / 640px、`:loading`、`@submit`；保存前需二次确认时传 `confirm` 文案），不直接写 `n-modal` |
| 确认 | 命令式确认用 `confirmDialog({ title, content, onPositiveClick })`（`@/utils`），默认跟随主题主色，危险操作传 `type: 'warning' \| 'error'`；不直接调 `window.$dialog`，不用 `info` 类型（固定蓝色，不随主题）；表格行内删除等就地确认用 `NPopconfirm` |
| 反馈 | 成功 `message.success('已保存')`（`@/utils`），不直接调 `window.$message`；失败由请求层统一提示，页面不重复弹错误 |
| 文案 | 简体中文、短动词：新建 / 编辑 / 删除 / 保存 / 取消 / 搜索 / 重置 |

`docs/design/prototype.html` 等静态原型新增或改版页面时，也按上表的布局与组件形态表达，保持与实际控制台一致。

## 新增一个页面

1. **接口**：在 `src/service/api/*.ts` 加 `fetchXxx` 函数（`request.Get/Post/Delete`，分页返回 `Service.PageResult<T>`）；实体类型加到 `src/typings/entities/`。
2. **页面**：`src/views/<目录>/index.vue`，按 [page-templates.md](references/page-templates.md) 写；弹窗 / 抽屉放同目录 `components/`。
3. **菜单**：菜单是数据，不在前端写死。在「菜单管理」新建，或写 alembic 迁移插入 `menu` 并授权给角色；`component` 填 `src/views` 下的目录（如 `/system/user`，前端自动拼 `/index.vue`）。
4. **权限**：后端新接口在平台启动时同步进 API 表；在「角色管理 → 设置权限」授权，前端按钮用对应权限码控制。
5. **校验**：`pnpm lint`（eslint + vue-tsc）通过，并在浏览器走一遍（`sh start-service.sh` 启动后访问 http://localhost:3001）。

## 不要做

- 不引入第二套 UI 库或 CSS 框架；不在页面里写大段 `<style>`，确有需要用 scoped 且只覆盖局部。
- 不在前端维护菜单、角色到菜单的映射或硬编码角色名判断权限。
- 不改 `src/layouts/`、`src/store/app/` 的 nova 原有行为来迁就单个页面；需要扩展时先确认是否该做成通用能力。
- 不新增在线依赖的组件（如需访问外网 CDN 的数据源）；内网部署不可用。
