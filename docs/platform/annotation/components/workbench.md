# 工作台 Workbench

> [工作台组件](README.md) · 源码 `web/src/components/custom/workbench/Workbench.vue`、`WorkbenchNode.vue`

模板的根。按布局树渲染标注界面，向所有组件提供数据与命令，并负责保存、提交、查看与导出。

## 演示

### 空白工作台

```xml
<Workbench/>
```

新建模板的默认值。渲染为空态，保存模板时提示「工作台为空」。

### 纵向排列

```xml
<Workbench>
  <ButtonBar>…工具栏…</ButtonBar>
  <Grid columns="2">…</Grid>
</Workbench>
```

`<Workbench>` 本身按纵向列表排布子节点：按钮栏按内容高度，网格占满剩余高度。

### 旧模板

根为 `<View>` 的模板按以下默认布局渲染，画布内容就是原 XML：

```xml
<Workbench>
  <ButtonBar>
    <Button action="undo"/>
    <Button action="redo"/>
    <Button action="view-data"/>
    <Button action="log"/>
    <Spacer/>
    <Button action="prev"/>
    <Button action="next"/>
    <Button action="save"/>
    <Button action="submit"/>
  </ButtonBar>
  <Canvas>（原 &lt;View&gt;）</Canvas>
</Workbench>
```

### 模板预览

```vue
<Workbench :config="xml" :data="sampleData" :item="{ name: '样例', index: 1, total: 1 }" preview />
```

`preview` 下保存、提交、上一份、下一份只记日志，不触发事件。

## 生命周期

| 阶段 | 时机 | 行为 |
|------|------|------|
| 解析 | `config` 变化 | 解析布局树并校验；结构错误只显示错误，规则错误（如 `toName` 无效）显示错误并照常渲染 |
| 初始化表单 / 表格 | 解析后、`result` 变化 | 按表单 `name` 建值对象，从结果中 `type: km.form` 的条目回填；可编辑表格从 `type: km.table` 回填，其余表格用样例行 |
| 挂载 | 首次渲染 | 递归渲染容器与组件；画布新建编辑器并选中（或新建）一份标注 |
| 切换条目 | `data` / `result` 变化 | 表单回填、画布重建编辑器；`item.id` 变化时清空日志 |
| 交互 | 点击按钮或宿主调用 `run` | 执行命令，写日志，按需发出事件 |
| 卸载 | 离开页面 | 销毁编辑器 |

## 结果与快照

提交给业务的结果是一个数组：Label Studio 结果原样保留，每个表单、每个可编辑表格各追加一条。

```json
[
  { "type": "rectanglelabels", "from_name": "label", "to_name": "image", "value": { "x": 12, "y": 30, "width": 20, "height": 15, "rectanglelabels": ["印章"] } },
  { "type": "km.form", "from_name": "meta", "value": { "title": "关于开展档案数字化质量检查的通知", "secret": "内部" } },
  { "type": "km.table", "from_name": "files", "value": { "rows": [{ "seq": 1, "title": "企业设立登记申请书" }] } }
]
```

「查看数据」与导出的快照：

| 字段 | 内容 |
|------|------|
| `item` | 当前条目 `id`、`name`、`index` |
| `data` | 条目数据 |
| `forms` | 表单名 → 字段值 |
| `tables` | 表格名 → 行数据 |
| `result` | Label Studio 结果 |

## API

### Workbench Props

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| config | `string` | 必填 | 模板 XML，根为 `<Workbench>` 或 `<View>` |
| data | `Record<string, unknown>` | 必填 | 条目数据，即编辑器 `task.data` |
| result | `Record<string, unknown>[] \| null` | `undefined` | 已有结果，含表单值，用于回显 |
| item | `WorkbenchItem` | `undefined` | 当前条目：`{ id?, name, index, total }`，用于快照与导出文件名 |
| has-prev | `boolean` | `false` | 是否有上一份 |
| has-next | `boolean` | `false` | 是否有下一份；为真时「提交」显示为「提交并下一份」 |
| loading | `boolean` | `false` | 保存 / 提交进行中 |
| preview | `boolean` | `false` | 模板预览模式 |

### Workbench Events

| 名称 | 参数 | 说明 |
|------|------|------|
| save | `(result: Record<string, unknown>[])` | 保存草稿；宿主调用保存接口并带 `draft: true` |
| submit | `(result: Record<string, unknown>[])` | 提交；发出前已校验表单必填字段 |
| prev | `()` | 上一份 |
| next | `()` | 下一份 |

### Workbench Methods

通过 `ref` 调用：

| 名称 | 类型 | 说明 |
|------|------|------|
| run | `(action: string) => void` | 执行命令，`action` 同 [按钮](button.md) 的 `action` |
| snapshot | `() => { item, data, forms, tables, result }` | 当前快照 |
| getResult | `() => Record<string, unknown>[] \| null` | 当前结果（含表单）；画布未就绪时为 `null` |
