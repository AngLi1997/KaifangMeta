# 间隔 Spacer

> [工作台组件](README.md) · 布局 · 放在任意容器

留出空白。放在按钮栏里时占满剩余宽度，把后面的按钮推到右侧；放在列表、面板、网格里时是一段 16px 的空白，用来隔开两个组件。可以放多个。

## 演示

### 推开两组按钮

```xml
<ButtonBar>
  <Button action="undo"/>
  <Button action="redo"/>
  <Spacer/>
  <Button action="save"/>
  <Button action="submit"/>
</ButtonBar>
```

撤销、重做靠左，保存、提交靠右。放两个 `<Spacer/>` 时，中间的按钮居中。整栏统一靠左、靠右、居中或分散时，用按钮栏的 `align`，不用间隔。

### 隔开两个面板

```xml
<Workbench>
  <Panel title="档案详情">…</Panel>
  <Spacer/>
  <Panel title="内容">…</Panel>
</Workbench>
```

两个面板之间多出 16px 空白（加上容器自身的间距）。需要更大的空白时设 `size`，如 `<Spacer size="10%"/>`。

## API

### Spacer 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| size | `string` | 16px | 在列表、面板、根里的占比（百分比）；按钮栏里不生效 |
