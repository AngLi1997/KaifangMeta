# 按钮栏 ButtonBar

> [工作台组件](README.md) · 放在任意布局容器

横向排列按钮与间隔，并控制它们的对齐方式。[按钮](button.md)只能放在按钮栏里，在设计器中把按钮拖到面板、列表等其他容器时，会自动包一层按钮栏。

## 演示

### 工具栏

```xml
<ButtonBar>
  <Button action="undo"/>
  <Button action="redo"/>
  <Spacer/>
  <Button action="save"/>
  <Button action="submit"/>
</ButtonBar>
```

撤销、重做靠左，`<Spacer/>` 把保存、提交推到右侧。

### 对齐

```xml
<ButtonBar align="end">
  <Button action="save"/>
  <Button action="submit"/>
</ButtonBar>
```

| align | 效果 |
|-------|------|
| `start` | 左对齐（默认） |
| `center` | 居中 |
| `end` | 右对齐 |
| `between` | 分散对齐：首尾贴边，中间等距 |

| valign | 效果 |
|--------|------|
| `top` | 上对齐 |
| `center` | 垂直居中（默认） |
| `bottom` | 下对齐 |

- 栏内有 `<Spacer/>` 时，间隔先占满剩余宽度，`align` 不再起作用。
- 按钮栏在列表里按内容高度显示；放进网格单元格等有剩余高度的位置时，`valign` 决定按钮靠上、居中还是靠下。
- 一行放不下时自动换行。

## 生命周期

无自身状态，随工作台渲染。

## API

### ButtonBar 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| align | `'start' \| 'center' \| 'end' \| 'between'` | `'start'` | 水平对齐 |
| valign | `'top' \| 'center' \| 'bottom'` | `'center'` | 垂直对齐 |
| gap | `number` | `8` | 间距（px） |

### 可放的子节点

[按钮](button.md)、[间隔](spacer.md)。
