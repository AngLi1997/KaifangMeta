# 网格 Grid

> [工作台组件](README.md) · 布局容器

二维排布：按行列放置子节点，子节点可跨行、跨列。需要左右分栏、多块并列或跨行跨列时用网格；只是一列按比例排开时用[列表](list.md)。

## 演示

### 两栏

```xml
<Grid columns="2">
  <Panel title="档案详情">…</Panel>
  <Panel title="内容">…</Panel>
</Grid>
```

### 跨行、跨列

```xml
<Grid columns="3" rows="2">
  <Panel title="内容" rowSpan="2">…</Panel>
  <Panel title="基本信息" colSpan="2">…</Panel>
  <Panel title="卷内文件目录" colSpan="2">…</Panel>
</Grid>
```

左侧「内容」占两行，右侧两块各占两列。

- 子节点默认撑满所在单元格。
- 不设 `rows` 时行数随子节点自动增加，各行平分剩余高度；设了 `rows` 时固定行数、等高。
- `colSpan` 超过列数、`rowSpan` 超过固定行数时按上限处理。
- 设计器中右键子节点 →「跨列」「跨行」可快捷设置。

## 生命周期

无自身状态，随工作台渲染。

## API

### Grid 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| columns | `number` | `2` | 列数，设计器中可选 1–6 |
| rows | `number` | 自动 | 固定行数，1–12；不设为自动 |
| gap | `number` | `12` | 间距（px） |

### 子节点属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| colSpan | `number` | `1` | 跨列数 |
| rowSpan | `number` | `1` | 跨行数 |
