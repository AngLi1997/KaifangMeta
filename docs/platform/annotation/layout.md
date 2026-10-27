# 工作台布局与插件

> 平台 · 数据标注模块。标注工作台的布局怎么搭、平台组件有哪些、数据怎么查看与导出。组件用法见[工作台组件](components/README.md)。相关：[场景模板](templates.md)、[Label Studio 集成与语言](labelstudio.md)、[业务系统对接](integration.md)。

## 要点

- **容器自由嵌套，默认空白**：不预设固定区域；工作台从空白开始，用网格、横向 / 纵向列表、面板搭出界面，容器可任意嵌套，按钮栏、表单、数据表格、画布、间隔放进任意容器。
- **布局是模板的一部分**：根标签为 `<Workbench>` 时按布局渲染，`<Canvas>` 内的 `<View>` 原样交给 Label Studio；根标签仍为 `<View>` 的旧模板按默认布局（工具栏 + 画布 + 状态栏）渲染，无需迁移。
- **代码与拖拽编辑同一棵布局树**：XML 解析成布局树，拖拽设计器改的也是布局树，再序列化回 XML；两种方式随时切换。
- **Label Studio 原生标签也可拖拽，但只放进画布**：图像、文本、矩形标签、单 / 多选等常用标签进入组件库，拖入 `<Canvas>` 内；平台组件放容器，原生标签放画布，两层不混放。
- **组件由平台内置、模板只做声明与配置**：不开放自定义 JS（与[场景模板](templates.md)一致）。
- **组件按期开放、克制增加**：先做公共能力（保存、提交、撤销、重做、查看数据、导出），再开放 Label Studio 原生标签，然后是布局容器、通用表单与数据表格，著录表单的框选回填、数据源等在其上扩展；新组件至少有两个真实场景才进内置库。
- **联动靠「命令 + 事件 + 共享上下文」**：组件只声明自己能发出的事件和能执行的命令，模板用 `<Link>` 把两者接起来；不写代码、组件间不互相引用。
- **业务接口只走登记的数据源**：数据表格读写业务数据经平台代理调用应用登记的接口，模板里只写数据源编码，不写 URL；数据源接入前先用静态样例数据。
- **工作台本身不存状态**：界面上能看到的一切都来自「条目数据 + 标注快照」，可随时「查看数据」并导出 JSON / YAML；表单值随标注结果保存，重新打开按结果还原。

## 布局容器

| 容器 | 标签 | 排布 | 主要属性 |
|------|------|------|---------|
| 网格 | `<Grid>` | CSS Grid，等宽列，子节点可跨行跨列 | `columns`、`rows`、`gap`；子节点 `colSpan`、`rowSpan` |
| 横向列表 | `<List direction="horizontal">` | 横向 flex | `gap`；子节点 `size` |
| 纵向列表 | `<List direction="vertical">` | 纵向 flex | `gap`；子节点 `size` |
| 面板 | `<Panel>` | 带标题的卡片，内部纵向排列，内容超出时滚动 | `title` |
| 按钮栏 | `<ButtonBar>` | 横向排列按钮与间隔 | `align`、`valign`、`gap` |
| 间隔 | `<Spacer>` | 按钮栏里占满剩余宽度；其他容器里是一段 16px 空白，可设占比 | 子节点 `size` |

- `<Workbench>` 本身是一个纵向列表，空白时什么也不渲染。
- 按钮只能放进[按钮栏](components/button-bar.md)（拖到其他容器时自动包一层）：按钮栏横向排列，可设左 / 中 / 右 / 分散与上 / 中 / 下对齐，`<Spacer/>` 把后面的按钮推到右侧。
- 列表里的尺寸自动分配：按钮栏按内容高度；其他组件与容器默认撑满并平分剩余空间，`size` 指定百分比占比。
- 网格的行高按内容与剩余空间分配（或用 `rows` 固定行数），子节点 `colSpan` / `rowSpan` 跨列、跨行。

```
Workbench（纵向）
├─ ButtonBar：撤销 重做 查看数据 日志 ⟷ 上一份 下一份 保存 提交
├─ Grid 2 列
│  ├─ List 纵向
│  │  ├─ Panel 档案详情 → Form
│  │  └─ Panel 卷内文件目录 → DataTable
│  └─ Panel 内容 → Canvas（Label Studio）
```

## 代码定义

```xml
<Workbench>
  <ButtonBar>
    <Button action="undo"/>
    <Button action="redo"/>
    <Button action="view-data"/>
    <Spacer/>
    <Button action="save"/>
    <Button action="submit"/>
  </ButtonBar>
  <Grid columns="2">
    <List direction="vertical">
      <Panel title="档案详情">
        <Form name="meta" columns="2">
          <Field name="title" label="题名" type="text" required="true"/>
          <Field name="secret" label="密级" type="select" options="公开,内部,秘密"/>
          <Field name="date" label="成文日期" type="date"/>
        </Form>
      </Panel>
      <Panel title="卷内文件目录">
        <DataTable name="files">
          <Column key="seq" title="序号" type="number" width="80"/>
          <Column key="title" title="文件题名"/>
        </DataTable>
      </Panel>
    </List>
    <Panel title="内容">
      <Canvas>
        <View>
          <Image name="image" value="$image"/>
          <RectangleLabels name="label" toName="image">
            <Label value="印章"/>
          </RectangleLabels>
        </View>
      </Canvas>
    </Panel>
  </Grid>
</Workbench>
```

- `$变量` 与 `$params.*` 规则同模板 XML，由 `data_schema`、`params` 校验。
- 工作台解析 `<Workbench>`，`<Canvas>` 的子树原样序列化后交给编辑器；平台标签不会进入 Label Studio。
- 表单、表格的 `name` 即它在快照里的键，同一模板内唯一；一个模板最多一个画布，可以没有画布（纯表单著录）。

## 拖拽设计器

场景模板页增加「布局」页签，与「XML」页签编辑同一份模板；新建模板默认打开「布局」，从空白开始：

| 部分 | 作用 |
|------|------|
| 左侧组件库 | 按「布局 / 组件 / 按钮 / Label Studio / Label Studio 对象 / 控件 / 视觉」分组；拖到容器中放置，不允许的位置不响应；已放置的唯一组件（按钮、画布）置灰；鼠标悬停 1 秒弹出外观预览，开始拖动即关闭 |
| 中间画板 | 按真实嵌套显示容器，组件默认撑满所在位置；光标靠近组件的上 / 下 / 左 / 右边时插到那一侧（与排列方向垂直的一侧自动包成列表、两者各占一半），光标在容器内部时高亮整个容器、放进该容器（规则见[布局设计器](components/designer.md#拖放规则)）；画布是嵌套放置区，原生标签只能拖入其中 |
| 右侧属性 | 容器编辑方向 / 列数 / 间距 / 标题，子节点编辑占比或跨列；表单编辑字段（标签、字段名、类型、必填、选项），数据表格编辑列（列名称、字段、类型、宽度）；原生控件编辑 `name`、`toName` 与选项 |
| 代码视图 | 随时切到 XML；XML 修改后回到画板即重新解析 |

- 两种编辑方式只有一份数据：布局树 ↔ XML 双向转换。拖拽保存时按规范格式重新序列化，XML 里的注释与自定义缩进不保留；画布内组件库未收录的标签（如 `<Relations>`、带 `<Style>` 的 `<View>`）作为「原始 XML」块原文保留，只能在 XML 视图编辑。
- XML 解析失败时画板只读并提示错误位置，不覆盖代码。
- 预览区使用样例数据渲染，与工作台同一套组件。

## Label Studio 原生标签

画布内就是一份 Label Studio `<View>`，组件库收录常用标签，拖入画布即生成带默认属性的标签：

| 分组 | 标签 | 默认属性 |
|------|------|---------|
| 对象 | `Image`、`Text`、`HyperText`、`Audio`、`Video`、`Paragraphs` | `name` 自动编号，`value` / `valueList` 指向 `$变量` |
| 控件 | `Rectangle`、`RectangleLabels`、`PolygonLabels`、`KeyPointLabels`、`BrushLabels`、`Labels`、`Choices`、`Taxonomy`、`TextArea`、`Number`、`DateTime`、`Rating` | `name` 自动编号，`toName` 默认画布内第一个对象；带标签 / 选项的控件预置示例选项 |
| 视觉 | `Header` | `value` |

```xml
<Canvas>
  <View>
    <Image name="page" valueList="$pages"/>
    <Rectangle name="ocr_box" toName="page"/>
    <RectangleLabels name="layout" toName="page">
      <Label value="印章"/>
      <Label value="签名"/>
    </RectangleLabels>
    <Choices name="secret" toName="page" choice="single">
      <Choice value="公开"/>
      <Choice value="内部"/>
    </Choices>
  </View>
</Canvas>
```

- **只能放在画布内**：一个工作台只有一个编辑器实例，控件靠 `toName` 引用同一实例里的对象，结果也由编辑器统一输出；把原生标签拆到画布外的面板需要多实例或跨实例联动，代价大于收益。需要放到画布外的输入（如著录字段）用平台组件 `RecordForm`。
- **校验**：画布内至少一个对象标签；`name` 不重复；控件的 `toName` 必须指向画布内对象，否则设计器标红、保存与切回拖拽视图时报错。
- 原生标签的属性与选项照搬 Label Studio 写法，平台不改语义；组件库只决定「能拖什么」，XML 视图可写编辑器支持的任何标签。

## 插件

插件由平台前端实现、随工作台发布，模板只能引用已有插件类型：

```ts
interface WorkbenchPlugin<P, V> {
  type: string                         // 标签名，如 RecordForm
  kind: 'container' | 'leaf'          // 容器可嵌套子节点，组件不可
  props: JSONSchema                    // 属性契约：设计器生成属性面板、保存时校验
  getValue(): V                        // 写入快照
  setValue(v: V): void                 // 按快照还原
  validate?(): Issue[]                 // 提交前校验，汇总到状态栏
}
```

- 组件之间只经工作台联动通信（见下文「组件联动」），不互相引用。
- 插件不保存状态：值只通过 `getValue` 进入快照，不使用浏览器存储。

### 图像动作栏 `ImageActions`（不实现）

> 编辑器已自带缩放、平移，`<Image zoomControl="true" rotateControl="true">` 可显示缩放与旋转按钮，按「优先保留 Label Studio 能力」不再做平台组件，见[画布](components/canvas.md#优先用-label-studio-自带能力)。下表保留为原设计记录。

| 属性 | 说明 |
|------|------|
| `toName` | 绑定的 `Image` 名称 |
| `actions` | `rotate-left`（左旋 90°）、`rotate-right`（右旋 90°）、`zoom-in`、`zoom-out`、`fit`（适应）、`reset` |
| `position` | `top`（默认，面板顶部）/ `left`（竖排工具条） |

- 调用编辑器 `Image` 对象的旋转、缩放方法，与编辑器内操作等价，标注区域随图像一起变换；具体方法以锁定的 1.23.2 为准，封装在 `AnnotationCanvas` 内。
- 快捷键：`[` / `]` 左右旋、`+` / `-` 缩放、`0` 适应。
- 旋转角度、缩放比例属于界面状态，进快照的 `view` 段，便于导出时还原所见，不进 `result_mapping`。

### 著录表单 `RecordForm`

在已实现的通用表单 [`Form`](components/form.md) 上增加框选回填、预抽取与 AI 提取；字段定义与通用表单一致。

| 属性 | 说明 |
|------|------|
| `toName` | 框选回填所用的 `Image` |
| `ocr` | OCR 能力编码（能力目录中的算子，如 `ocr.general`）；不写则不显示框选回填 |
| `extract` | 预留：信息提取能力（AI 模型 / 流水线），第一期不实现 |
| `<Group title columns collapsible>` | 字段分组，`columns` 为栅格列数 |
| `<Field name label type …>` | 字段，见下表 |

| `type` | 控件 | 框选回填时的处理 |
|--------|------|----------------|
| `text` / `textarea` | 输入框 | 识别文本直接填入 |
| `number` | 数字 | 抽取数字 |
| `date` | 日期 | 解析常见格式（`2026年08月11日`、`2026-08-11`、`2026.8.11`）为 `YYYY-MM-DD`，失败则保留原文并标红 |
| `select` / `radio` | 下拉 / 单选 | 与选项做精确→包含匹配，命中则选中，否则提示未匹配 |
| `checkbox` | 多选 | 按分隔符拆分后逐项匹配 |

字段通用属性：`required`、`pattern`、`default`、`ocr`（是否允许框选回填）、`from`（预抽取字段名，用 predictions 预填）。

框选回填流程：

1. 点击字段旁的框选图标（或选中字段后按 `⌘O`），表单发 `ocr.arm(field)`，画布切换为 `ocr_box` 矩形工具，顶部提示「正在识别「主体名称」…」。
2. 用户在图像上框选，画布发 `canvas.region.created`，工作台按区域裁剪当前页。
3. 经平台能力接口调用 `ocr` 指定的算子，返回文本与置信度。
4. 按字段类型转换后填入，字段记录来源；`Esc` 取消。框选区域保留在画布上，可再次点击字段定位。

```json
{ "subject_name": "四川星辰信息技术有限公司",
  "_sources": { "subject_name": { "page": 1, "bbox": [0.33, 0.27, 0.56, 0.03], "text": "四川星辰信息技术有限公司", "confidence": 0.97, "by": "ocr.general" } } }
```

### 数据表格 `DataTable`

当前实现见[数据表格](components/data-table.md)（列可配、静态样例数据）；以下为接入业务数据源后的设计。

| 属性 | 说明 |
|------|------|
| `source` | 数据源编码（`应用.数据源`），在应用接入中登记，见下文 |
| `rowKey` | 行主键 |
| `editable` | 可编辑列；不写为只读 |
| `pageSize` | 分页大小，默认 10 |
| `<Column key title width type ellipsis>` | 列定义；列名称、宽度、类型由模板自定义 |
| `onChange` | `immediate`（单元格失焦即调用业务更新）/ `submit`（随提交一起，默认） |

数据源由业务应用登记，模板引用编码，平台代理调用：

```yaml
# 应用接入 · 标注数据源（智慧档案室）
sources:
  archive.files:
    list:   { method: GET,   path: /api/archives/{archive_id}/files }
    update: { method: PATCH, path: /api/archives/{archive_id}/files/{seq} }
    sample: [{ seq: 1, title: 企业设立登记申请书, author: 四川星辰信息技术有限公司, date: 2026-08-11, pages: "1-8" }]
```

```http
GET  /kaifang-meta/platform/annotation/v1/items/{item_id}/sources/archive.files
POST /kaifang-meta/platform/annotation/v1/items/{item_id}/sources/archive.files:update
Content-Type: application/json

{ "row": { "seq": 1, "title": "企业设立登记申请书" }, "rev": 3 }
```

- 路径参数（如 `archive_id`）从条目 `data` 中取；平台以应用 Service Token 调业务接口，并校验当前用户是该工单成员。
- 业务返回错误时单元格回滚并在状态栏日志记录；`submit` 模式下修改只进快照，随结果回传，由业务回写确认时处理。
- 表格数据也进快照：`rows`（当前值）与 `changes`（相对加载值的差异）。

### 按钮与侧栏组件

| 组件 | 放置 | 说明 |
|------|------|------|
| `Button action=` | 按钮栏 | `open`、`save`（草稿）、`view-data`、`undo`、`redo`、`prev`、`next`、`ocr-box`、`layout-analysis`（预留）、`export`（JSON / YAML）、`log`（弹窗查看本次操作日志）、`submit`；每个动作在一个模板内只放一次 |
| `Spacer` | 任意容器 | 间隔：按钮栏里把后面的按钮推到右侧，其他容器里是一段空白，可重复 |
| `InfoPanel` | 任意容器 | 只读键值，展示条目 `data` 中的业务信息 |
| `FileList` | 任意容器 | 多页 / 多文件列表，点击切换画布当前页 |
| `ItemList` | 任意容器 | 自由标注的条目列表 |

## 组件联动

组件不知道彼此存在，只对工作台暴露三样东西：

| 契约 | 方向 | 例子 |
|------|------|------|
| 事件 `emits` | 组件 → 工作台 | `filelist.select { index }`、`meta.focus { field }`、`canvas.region.created { name, page, bbox }`、`table.rowClick { row }` |
| 命令 `commands` | 工作台 → 组件 | `canvas.goto { page }`、`canvas.highlight { regionId }`、`meta.fill { field, value, source }`、`table.reload` |
| 上下文 `ctx` | 只读共享 | `item`（条目数据）、`page`、`selection`、`dirty`、`user`、`readonly` |

```ts
interface WorkbenchPlugin<P, V> {
  // …上文的 getValue / setValue / validate
  emits: Record<string, JSONSchema>                       // 能发出的事件及载荷
  commands: Record<string, (args: unknown) => void | Promise<void>>
}
```

### 三层联动

| 层 | 谁定义 | 内容 |
|----|-------|------|
| 内置联动 | 工作台外壳，不可关闭 | 保存 / 提交收集全部组件快照；撤销 / 重做走统一历史；任一组件变更置 `dirty`；`readonly` 时全部组件只读 |
| 约定联动 | 组件默认行为，模板可关 | 文件列表选中 → 画布翻页；表单字段聚焦 → 画布高亮该字段的来源框；画布选中来源框 → 表单聚焦对应字段 |
| 模板联动 | 模板作者用 `<Link>` 声明 | 任意「事件 → 命令」，可带条件与取值映射 |

```xml
<Links>
  <Link on="files.rowClick" do="canvas.goto" args="{ page: row.pages_from }"/>
  <Link on="canvas.region.created" when="region.name == 'ocr_box'" do="meta.fillFromRegion"/>
  <Link on="meta.change" when="field == 'subject_type'" do="table.reload" args="{ type: value }"/>
</Links>
```

- `when` / `args` 只允许取值路径、比较、字面量组成的表达式（不支持函数调用、赋值），在设计器「联动」页签里用下拉选择事件和命令、填写表达式，同样序列化为 XML。
- 命令按 `<Link>` 书写顺序串行执行；失败只记状态栏日志，不中断后续联动、不回滚已执行的命令。
- 保存模板时检查：事件与命令都存在；载荷字段与表达式引用的路径匹配；不允许形成环（A 的命令触发的事件再触发 A），有环拒绝保存。
- 联动只改界面与组件值，不直接调用业务接口；需要回写业务的仍由数据表格的数据源或提交流程完成。

### 公共能力如何跨组件

| 能力 | 做法 |
|------|------|
| 保存（草稿） | 依次调用各组件 `getValue` 与编辑器 `serializeAnnotation`，合成快照提交；不做校验 |
| 提交 | 先调用全部 `validate`，有错误时聚焦第一个出错组件并在状态栏列出；通过后保存并进入下一份 |
| 撤销 / 重做 | 工作台维护一条统一历史栈，每条记录来源（`canvas` 或某个组件）；撤销时交给来源处理：画布调用编辑器自身历史，平台组件用 `setValue` 恢复上一值。连续输入按 500ms 合并为一条 |
| 查看数据 / 导出 | 读取同一份快照，不经组件 |
| 只读 | 质检、已提交、业务锁定时 `ctx.readonly = true`，组件自行禁用编辑，按钮置灰 |

### Label Studio 侧的桥接

画布作为一个组件接入联动：把编辑器回调转成事件，把编辑器方法包成命令，均在 `AnnotationCanvas` 内完成。

| 编辑器回调 / 方法 | 联动名 |
|-------------------|--------|
| 区域创建、删除、选中 | `canvas.region.created` / `deleted` / `selected` |
| 标注更新 | `canvas.change`（同时写入统一历史） |
| 切换页、旋转、缩放 | 命令 `canvas.goto` / `rotate` / `zoom` |
| 高亮、选中区域 | 命令 `canvas.highlight` / `select` |

- 画布内原生标签之间的联动（如 `visibleWhen`、`perRegion`）仍由 Label Studio 自身处理，平台不重复实现。

## 数据查看与导出

工作台在任意时刻都能生成一份快照，界面所见即快照内容：

```yaml
item: { id: it_0012, task: at_7c1e, template: archive.register@2 }
view: { page: 1, rotation: 90, zoom: 0.57 }
plugins:
  meta:                       # RecordForm
    subject_name: 四川星辰信息技术有限公司
    credit_code: 915101008557726123
    _sources: { … }
  files:                      # DataTable
    rows: [ … ]
    changes: [{ seq: 1, title: [企业设立登记申请书, 企业设立登记申请书（正本）] }]
annotation: { result: [ … ] } # Label Studio 原始结果
```

- 「查看数据」以抽屉展示快照，可在 JSON / YAML 间切换、复制；「导出」下载 `{条目编号}.json` 或 `.yaml`。
- 保存草稿与提交存的就是这份快照；`result_mapping` 可引用插件值，如 `subject_name: plugin:meta.subject_name`。
- 嵌入业务页面时，宿主可经 iframe 消息 `km:snapshot` 取快照（见[业务系统对接](integration.md)）。

## 分期

已实现：布局解析与容器（网格含跨行跨列、横向 / 纵向列表、面板）、按钮栏（对齐方式）、设计器右键菜单、公共按钮（撤销、重做、上一份、下一份、查看数据、导出 JSON / YAML、日志、保存草稿、提交）、间隔、拖拽设计器与 Label Studio 原生标签、通用表单（字段与类型可配，值随结果保存，提交校验必填）、数据表格（列可配，静态样例数据）。统一历史目前只覆盖画布，联动、数据源、著录表单的框选回填未实现。

实际开发保持克制，按期开放组件，不一次铺开：

| 期 | 内容 | 开放的组件 |
|----|------|-----------|
| 一 | `<Workbench>` 解析与容器布局、统一历史 / 保存 / 提交 / 只读、快照查看与导出、内置联动 | 按钮：保存、提交、撤销、重做、查看数据、导出、日志 |
| 二 | 拖拽设计器（重排、悬停预览）、Label Studio 原生标签进入组件库、画布联动桥接 | 原生标签（对象、控件、视觉）；图像缩放旋转用 Label Studio 自带 |
| 三 | 约定联动与 `<Link>` 模板联动、联动页签 | 文件列表、信息栏 |
| 四 | 业务组件，每个组件有两个以上真实场景再做 | 通用表单、数据表格（静态样例）已先行实现；著录表单（预抽取）、数据表格数据源（`submit` / `immediate`） |
| 五 | 智能能力 | 框选 OCR 回填、`extract` AI 信息提取、版面分析 |
