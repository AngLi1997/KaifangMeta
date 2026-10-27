# 数据表格 DataTable

> [工作台组件](README.md) · 放在任意布局容器

按列定义显示一组行数据，可开启编辑。当前为静态样例数据，列名称、字段、类型、宽度、是否可编辑可在模板里配置；接入业务数据源的设计见[工作台布局与插件 · 数据表格](../layout.md#数据表格-datatable)。

## 演示

```xml
<DataTable name="files">
  <Column key="seq" title="序号" type="number" width="80"/>
  <Column key="title" title="文件题名"/>
  <Column key="date" title="成文日期" type="date" width="140"/>
</DataTable>
```

### 可编辑

表格设 `editable="true"` 后，再逐列设 `editable="true"` 的列渲染为输入控件（按列类型：文本输入、数字输入、日期选择），其余列仍只读。

```xml
<DataTable name="files" editable="true">
  <Column key="seq" title="序号" type="number" width="80"/>
  <Column key="title" title="文件题名" editable="true"/>
  <Column key="date" title="成文日期" type="date" width="140" editable="true"/>
</DataTable>
```

### 样例数据

每张表生成 5 行，按列类型取值：

| type | 第 n 行的值 |
|------|------------|
| `number` | `n` |
| `date` | `2026-08-1n` 起逐日递增 |
| `text`（默认） | `{列名称} n` |

### 在设计器中配置

选中表格后，右侧「可编辑」开关控制整表；「列」逐条编辑列名称、字段、类型与宽度，开启可编辑后每列多一个「可编辑」勾选，「添加列」追加一列。

## 生命周期

| 阶段 | 行为 |
|------|------|
| 初始化 | 工作台解析后、切换条目时，可编辑表格从结果中 `type: km.table`、`from_name` 为本表格 `name` 的条目回填；没有则用样例行 |
| 渲染 | 按列渲染行数据；表格占满所在容器剩余高度，内容超出时表格内滚动 |
| 编辑 | 修改可编辑列的单元格，值写入工作台表格数据 |
| 查看 / 导出 | 行数据进入快照 `tables.{name}` |
| 保存 / 提交 | 可编辑表格的全部行随结果保存；只读表格不进入结果 |

修改如何通知其他组件、宿主页面与业务系统见[组件事件与框选回填](../linkage.md)。

## 结果格式

```json
{ "type": "km.table", "from_name": "files", "value": { "rows": [{ "seq": 1, "title": "企业设立登记申请书（正本）", "date": "2026-08-11" }] } }
```

## API

### DataTable 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | `string` | 自动编号 `table`、`table_2` | 表格名，快照中的键，模板内唯一 |
| editable | `boolean` | `false` | 是否可编辑；开启后由各列 `editable` 决定哪些列可改 |

### Column 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| key | `string` | 必填 | 字段 |
| title | `string` | — | 列名称 |
| type | `'text' \| 'number' \| 'date'` | `'text'` | 列类型，决定样例值 |
| width | `number` | 自适应 | 列宽（px），只读列超出省略并悬停显示全文 |
| editable | `boolean` | `false` | 表格可编辑时，该列是否可编辑 |
