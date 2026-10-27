# 可复用清单（web/src）

新写之前先在这里找。路径均相对 `web/src`。

## 组件

| 组件 | 路径 | 用途 |
|------|------|------|
| `FormModal` | `components/common/FormModal.vue` | 表单弹窗：统一外观与「取消 / 保存」底栏；`v-model:show` `title` `size` `loading` `confirm` `@submit` |
| `SearchCard` | `components/common/SearchCard.vue` | 列表页查询区：行内表单 + 搜索 / 重置，回车触发搜索；`@search` `@reset` |
| `Pagination` | `components/common/Pagination.vue` | 分页，`:count="total"`，`@change(page, pageSize)`；配合 `usePageTable` |
| `DataTable` | `components/common/DataTable.vue` | 表格占满卡片剩余高度，分页栏贴底，空数据展示空态；单元格不换行，按列宽之和自动计算 `scroll-x`；`:count` 可省略（如树表） |
| `NovaIcon` | `components/common/NovaIcon.vue` | 按字符串渲染图标（菜单、动态数据）：`<nova-icon icon="icon-park-outline:api" :size="18" />` |
| `IconSelect` | `components/common/IconSelect.vue` | 图标选择器（菜单表单）；需联网加载图标集 |
| `HelpInfo` | `components/common/HelpInfo.vue` | 字段旁的问号提示，替代表单下方的说明文字 |
| `CopyText` | `components/custom/CopyText.vue` | ID / 密钥 + 一键复制；固定长度的 ID 传 `maxLength="none"` 完整显示，列宽用 `COL_WIDTH.id` |
| `DarkModeSwitch` / `LangsSwitch` | `components/common/` | 主题、语言切换（已在顶栏） |
| `CommonWrapper` | `components/common/CommonWrapper.vue` | 顶栏小按钮的统一外框 |
| `Watermark` | `components/common/Watermark.vue` | 全局水印（设置中开关） |
| 布局 | `layouts/` | `ProLayout`、标签栏、面包屑、搜索、设置抽屉；页面无需关心 |

## 反馈函数（`@/utils`）

| 函数 | 用途 |
|------|------|
| `confirmDialog(options)` | 确认框，默认主题主色；`type: 'warning' \| 'error'` 用于危险操作，按钮文案默认确定 / 取消 |
| `message.success / warning / error / info` | 全局消息 |

## Hooks

| Hook | 用途 |
|------|------|
| `usePageTable(fetchFn, initialQuery)` | 分页表格：`loading / rows / total / query / fetch / search / reset / changePage`；空查询条件自动不传 |
| `usePermission()` | `hasPermission(code \| code[])`：TSX 列里控制按钮显示 |
| `useBoolean(init)` | 布尔开关（loading、visible） |
| `useEcharts(el, options)` | ECharts 图表（随主题切换） |
| `useTableDrag({ tableRef, data })` | 表格行拖拽排序 |

## 表格列宽

目标：所有字段尽量单行展示，屏幕放不下时整表横向滚动，而不是挤压换行。

- 每列都设 `width`（长度固定或有上限的字段）或 `minWidth`（长度不定、可吸收剩余宽度的字段，同时设 `ellipsis: { tooltip: true }`）。不设宽度的列按 120px 计入滚动宽度。
- 宽度按「字段可能的最长内容」与「表头文字」两者取大，用 `utils/table.tsx` 估算，不手写像素：

  | 写法 | 含义 |
  |------|------|
  | `colWidth(半角字数, 全角字数, 附加宽度)` | 半角约 8px、全角约 14px，另加单元格内边距 32px；图标、复制按钮、标签内边距计入附加宽度 |
  | `COL_WIDTH.datetime` | `2026-10-27 12:20:24` |
  | `COL_WIDTH.id` | `sub`、租户 ID 等 18 位 ID + 复制图标（配合 `CopyText maxLength="none"`） |
  | `COL_WIDTH.status` | 两到三字状态标签 |
  | `COL_WIDTH.actions` | 两个文字按钮或「更多」 |

- 多个标签的列（租户、角色）用 `NSpace wrap={false}` 并设 `minWidth`。
- `DataTable` 不手写 `:scroll-x`：组件按各列 `width ?? minWidth` 之和自动计算。

```tsx
const columns: DataTableColumns<Entity.IdentityAccount> = [
  { title: '登录名', key: 'username', minWidth: colWidth(16), ellipsis: { tooltip: true } },
  { title: 'sub', key: 'sub', width: COL_WIDTH.id, render: row => <CopyText value={row.sub} maxLength="none" /> },
  { title: '邮箱', key: 'email', minWidth: colWidth(24), ellipsis: { tooltip: true } },
  { title: '控制台状态', key: 'is_active', width: colWidth(0, 5) },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
]
```

表格右侧操作列按钮统一使用 Naive UI 的 `text` 链接样式，可保留危险操作的 `type="error"` 等语义色。操作列调用 `utils/table.tsx` 的 `renderTableActions([...])`：最多两个按钮直接显示，超过两个时收进“更多”面板；触发按钮和面板内按钮都使用 `text`。操作列在横向滚动时使用 `fixed: 'right'`。

## 指令

| 指令 | 用途 |
|------|------|
| `v-permission="'post/api/v1/xxx'"` | 无权限时移除元素；支持数组（满足任一） |
| `v-copy="text"` | 点击复制 |

## 工具与服务

| 名称 | 位置 | 用途 |
|------|------|------|
| `request` | `service/http` | alova 实例，baseURL = 控制台 API（经网关）；返回 `{ isSuccess, data, total?, msg? }` |
| `fetchXxx` | `service/api/base.ts`、`system.ts` | 已有接口函数，先查再加 |
| `startLogin` / `logout` / `getToken` | `service/auth` | OIDC 登录、退出、内存 Token；页面一般不直接用 |
| `renderIcon(icon)` | `utils/icon.ts` | 下拉菜单、`NMenu` 等需要渲染函数的图标 |
| `local` / `session` | `utils/storage.ts` | 带前缀的存储（只存界面偏好，不存 Token） |
| `arrayToTree` | `utils/array.ts` | 扁平 id / pid 转树 |
| `useAuthStore()` | `store/auth.ts` | `userInfo`、`permissions`、`isSuperUser`、`logout()` |
| `useAppStore()` | `store/app` | 主题、布局模式、语言等界面设置 |

UnoCSS shortcuts（`unocss.config.ts`）：`wh-full`、`flex-center`、`flex-col-center`、`flex-x-center`、`flex-y-center`。
