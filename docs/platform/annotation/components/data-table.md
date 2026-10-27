# 数据表格 DataTable

> [工作台组件](README.md) · 放在任意布局容器

按列定义显示一组行数据。当前为静态样例数据，列名称、字段、类型、宽度可在模板里配置；接入业务数据源的设计见[工作台布局与插件 · 数据表格](../layout.md#数据表格-datatable)。

## 演示

```xml
<DataTable name="files">
  <Column key="seq" title="序号" type="number" width="80"/>
  <Column key="title" title="文件题名"/>
  <Column key="date" title="成文日期" type="date" width="140"/>
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

选中表格后，右侧「列」逐条编辑列名称、字段、类型与宽度，「添加列」追加一列。

## 生命周期

| 阶段 | 行为 |
|------|------|
| 渲染 | 按列生成样例行；表格占满所在容器剩余高度，内容超出时表格内滚动 |
| 查看 / 导出 | 行数据进入快照 `tables.{name}` |

表格只读，不进入提交结果。

## API

### DataTable 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | `string` | 自动编号 `table`、`table_2` | 表格名，快照中的键，模板内唯一 |

### Column 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| key | `string` | 必填 | 字段 |
| title | `string` | — | 列名称 |
| type | `'text' \| 'number' \| 'date'` | `'text'` | 列类型，决定样例值 |
| width | `number` | 自适应 | 列宽（px），超出省略并悬停显示全文 |
