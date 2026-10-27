# Label Studio 集成与语言

> 平台 · 数据标注模块。Label Studio 编辑器如何构建、嵌入、汉化，以及平台级中英文控制。相关：[数据标注](overview.md)、[场景模板](templates.md)。

## 要点

- **只用编辑器**：从 Label Studio 社区版主仓库 `web/libs/editor` 源码构建（1.11 起编辑器不再单独发布 npm 包），锁定 1.23.2，发布为内网包 `@kaifang-meta/label-studio-editor`。
- **不部署服务、不进数据**：没有 Label Studio 的 Django 服务、数据库和用户；编辑器只接收「模板 XML + 条目数据 + predictions」并输出标注 JSON。
- **同一版本出两套语言**：英文原版与汉化版各构建一份，汉化优先采用适配 1.23.2 的社区中文语言包，缺漏由补译表补齐。
- **语言由平台设置控制**：默认语言、编辑器语言、是否允许用户切换三项平台级设置，控制台、标注工作台、编辑器统一生效。
- **只有一个接触点**：工作台组件 `AnnotationCanvas` 封装编辑器，换编辑器或升级版本只改这里。

## 选型

| 方案 | 结论 | 理由 |
|------|------|------|
| 从零自研画布 | 不采用 | 多模态画布工作量最大，且与业务无关 |
| 部署汉化版 Label Studio 整站，经其 API 同步 | 不采用 | 数据在两套库间同步；社区版没有分配与审核，仍要自建；多一套服务、数据库和用户体系 |
| Label Studio Embed SDK | 不采用 | 企业版功能，仍依赖其服务端 |
| **源码构建编辑器（中 / 英），嵌入工作台** | **采用** | 模态与模板最全；数据、流程、账号、界面外壳全部自控 |
| LabelU | 备选 | 原生中文、组件可嵌入；某模态需要替换时使用 |

## 当前实现

控制台已落地「数据标注 → 标注工单 / 场景模板」，表在 `annotation` schema（迁移 `0016`、`0017`），接口挂在控制台 `/annotation/*`，授予管理员与租户管理员：

| 页面 | 路由 | 内容 |
|------|------|------|
| 标注工单 | `/annotation/task` | 工单列表、新建工单（名称 + 场景模板，建单时快照模板 XML） |
| 工单详情 | `/annotation/task-detail?id=` | 工单信息、上传数据（图像 / 视频 / 音频 / UTF-8 文本）、条目列表、开始标注 |
| 标注工作台 | `/annotation/workbench?task_id=` | 按模板布局渲染（[工作台组件](components/README.md)）：撤销 / 重做、上一份 / 下一份、查看数据与 JSON / YAML 导出、保存草稿、提交并下一份，已标注条目回显结果 |
| 场景模板 | `/annotation/template` | 内置 6 个系统模板，新建、编辑或预览 |
| 模板编辑 | `/annotation/template-edit?id=` | 左侧模板信息与 XML 编辑器（CodeMirror，高亮 + Label Studio 标签 / 属性补全）；右侧带边框的预览区，铺满可用空间，窄于 1280px 时等比缩小，XML 不合法时只提示错误；标题旁按钮组切换「XML / 布局 / 预览」：布局为拖拽布局设计器，预览按实际尺寸渲染工作台 |

与本文目标设计的差异：

| 项 | 当前 | 目标 |
|----|------|------|
| 编辑器 | npm `@heartexlabs/label-studio@1.4.0`（1.8.0 的 npm 包缺少构建产物），在同源 iframe 中运行 | 1.23.2 源码构建，只改 `web/src/components/custom/AnnotationCanvas.vue` |
| 汉化 | 运行时补译表（随控制台语言 `zhCN` 生效） | 构建期汉化补丁 + 平台语言设置 |
| 数据 | 控制台上传，经后端转存 MinIO（单文件 ≤ 50 MB） | 业务清单分片、引用模式 |
| 流程 | 打开即可标注，提交后条目「已标注」，全部提交工单「已完成」 | 分包领取 / 指定、质检、结果版本 |

## 构建

```bash
git clone --branch 1.23.2 https://github.com/HumanSignal/label-studio.git
cd label-studio/web
yarn install --frozen-lockfile
yarn nx build editor                         # 英文原版 → dist/en-US
git apply ../../km-patches/zh-CN/*.patch     # 汉化补丁
yarn nx build editor                         # 汉化版 → dist/zh-CN
```

| 产物 | 说明 |
|------|------|
| `@kaifang-meta/label-studio-editor@1.23.2-km.N` | 一个包两套产物：`en-US/main.{js,css}`、`zh-CN/main.{js,css}` |
| `km-patches/zh-CN/` | 由社区中文语言包整理出的编辑器汉化补丁，与构建脚本同仓库维护 |
| `editor-zh.json` | 补译表：补丁未覆盖的文案，工作台加载后做文案映射 |

- 控制台前端 `web/` 依赖此包，按路由懒加载，只下载当前语言那一份，不进入首屏包。
- 版本锁定，不跟随上游自动升级；升级时整体重做补丁、重跑汉化与模态回归。

## 嵌入接口

```ts
const LabelStudio = await loadEditor(locale)   // 按生效语言加载 en-US 或 zh-CN 产物

new LabelStudio(el, {
  config: templateXml,                         // 已渲染参数的模板 XML
  interfaces: ['panel', 'controls', 'side-column', 'predictions:menu'],
  user: { pk: sub, firstName: displayName },   // 来自平台身份目录
  task: { id: itemId, data: item.data, predictions: item.predictions, annotations: item.history },
  onLabelStudioLoad: ls => ls.annotationStore.addAnnotation({ userGenerate: true }),
  onSubmitAnnotation: (ls, ann) => save(ann.serializeAnnotation()),
  onUpdateAnnotation: (ls, ann) => saveDraft(ann.serializeAnnotation()),
})
```

- 提交、跳过、上一份 / 下一份、领取、质检按钮由工作台外壳提供；不开放编辑器自带的标注列表与删除，避免与工单流程冲突。
- `user` 只用于编辑器内显示，身份以平台 Token 为准，不在编辑器里建用户。
- `item.data` 中的文件地址是平台文件地址（见 [业务系统对接](integration.md)），不是业务存储地址。
- 草稿每 30 秒自动保存；自由标注保存时带 `rev`，冲突时提示刷新。

## 汉化

| 来源 | 用法 |
|------|------|
| 社区中文语言包（适配 1.23.2，Apache-2.0） | 首选：整理出涉及编辑器的中文文案，转为对 `web/libs/editor` 的补丁 |
| 补译表 `editor-zh.json` | 语言包未覆盖的编辑器文案（工具提示、区域面板、快捷键说明） |
| 模板 XML | 标签名、字段名、提示语由模板作者直接写，编辑器不翻译 |
| 工作台外壳 | 控制台前端 vue-i18n 语言包 `web/locales/zh_CN.json` / `en_US.json` |

汉化覆盖率在第一期 POC 按模态验收，缺漏只补进补译表，不改流程。

## 平台级语言控制

平台设置（控制台「平台设置 · 界面语言」，系统租户管理员维护）：

| 设置 | 取值 | 默认 | 说明 |
|------|------|------|------|
| `ui.locale.default` | `zh-CN` / `en-US` | `zh-CN` | 控制台、标注工作台、看板、查看器、登录页的默认语言 |
| `ui.locale.editor` | `follow` / `zh-CN` / `en-US` | `follow` | 标注编辑器语言；`follow` 跟随界面语言。可单独锁定为英文原版（如外籍标注员或汉化有缺陷时） |
| `ui.locale.user_switch` | `true` / `false` | `true` | 是否允许用户在顶栏切换语言；关闭后所有人强制使用平台语言 |

生效顺序：

```
用户选择（允许切换时，存用户偏好）  >  平台默认语言
编辑器语言 = ui.locale.editor == follow ? 界面语言 : ui.locale.editor
```

- 设置存平台控制台 `console_authz` 下的平台设置表，随用户信息接口下发；修改后用户下次加载页面生效，不需要重新构建或重启。
- 用户偏好按 `sub` 存服务端，换浏览器、从业务系统打开工作台都保持一致。
- 当前实现以构建变量 `VITE_DEFAULT_LANG` 决定默认语言、用户切换存浏览器本地；本设计以平台设置取代构建变量，构建变量只作为平台设置缺失时的兜底。
- 场景模板内容（标签名）不随语言切换；需要双语标签的模板在 XML 中直接写双语。
