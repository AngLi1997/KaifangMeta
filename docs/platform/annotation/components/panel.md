# 面板 Panel

> [工作台组件](README.md) · 布局容器

带标题的卡片，内部纵向排列子节点；内容超出高度时在面板内滚动。

## 演示

```xml
<Panel title="档案详情">
  <Form name="meta">…</Form>
</Panel>
```

### 嵌套

```xml
<Panel title="卷内信息">
  <ButtonBar>
    <Button action="export"/>
  </ButtonBar>
  <DataTable name="files">…</DataTable>
</Panel>
```

面板内子节点的尺寸规则同[纵向列表](list.md)。

## 生命周期

无自身状态，随工作台渲染。

## API

### Panel 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | `string` | `'面板'` | 标题；为空时不显示标题栏 |
