# 画布 Canvas

> [工作台组件](README.md) · 组件库「Label Studio」分组 · 放在任意布局容器，一个模板最多一个 · 源码 `web/src/components/custom/AnnotationCanvas.vue`

承载 Label Studio 编辑器。`<Canvas>` 内是一份 Label Studio `<View>`，原样交给编辑器，Label Studio 原生标签只能放在这里。

## 演示

### 基础用法

```xml
<Canvas>
  <View>
    <Image name="image" value="$image"/>
    <RectangleLabels name="label" toName="image">
      <Label value="印章"/>
      <Label value="签名"/>
    </RectangleLabels>
    <Choices name="secret" toName="image" choice="single">
      <Choice value="公开"/>
      <Choice value="内部"/>
    </Choices>
  </View>
</Canvas>
```

### 组件库收录的原生标签

| 分组 | 标签 | 拖入后的默认属性 |
|------|------|----------------|
| 对象 | `Image`、`Text`、`HyperText`、`Audio`、`Video` | `name` 自动编号，`value="$变量"` |
| 控件 | `Rectangle`、`RectangleLabels`、`PolygonLabels`、`KeyPointLabels`、`BrushLabels`、`Labels`、`Choices`、`Taxonomy`、`TextArea`、`Number`、`DateTime`、`Rating` | `name` 自动编号，`toName` 为画布内第一个对象；带选项的控件预置两项示例 |
| 视觉 | `Header` | `value="标题"` |

未收录的标签（如 `Relations`、`Paragraphs`、嵌套 `View`）可以在 XML 中写，设计器里显示为「原始 XML」块并原文保留。

### 优先用 Label Studio 自带能力

编辑器自带的功能不再做平台组件：

| 需求 | 用 Label Studio |
|------|----------------|
| 图像缩放、平移 | 画布左侧工具栏自带；`<Image zoomControl="true">` 显示缩放按钮 |
| 图像旋转 | `<Image rotateControl="true">` |
| 删除全部区域、区域列表、关系 | 画布右侧面板自带 |
| 画布内的分类、文本、数字、日期、评分输入 | `Choices`、`TextArea`、`Number`、`DateTime`、`Rating`、`Taxonomy` |
| 画布内的标题文字 | `Header` |

撤销、重做在当前编辑器中没有按钮，由平台[按钮](button.md)提供，调用的是编辑器自身的标注历史。

## 生命周期

| 阶段 | 时机 | 行为 |
|------|------|------|
| 创建 | 挂载，或 `config` / `data` / `result` 变化 | 新建同源 iframe 加载编辑器（避免重建时残留上一份布局） |
| 就绪 | 编辑器 `onLabelStudioLoad` | 回显已有结果，没有则新建一份标注并选中 |
| 校验 | 创建前 | XML 无法解析时只显示错误，不交给编辑器 |
| 销毁 | 卸载 | 调用编辑器 `destroy` |

## 校验规则

保存模板、切回拖拽视图时检查：

- 画布内至少一个对象标签；
- `name` 不重复；
- 控件的 `toName` 指向画布内的对象（设计器中不满足的控件标红）。

画布内有「原始 XML」块时跳过后两项，由编辑器渲染时报错。

## API

### Canvas 属性

无。`<Canvas>` 只能包含一个 `<View>`。

### AnnotationCanvas Props

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| config | `string` | 必填 | Label Studio `<View>` XML |
| data | `Record<string, unknown>` | 必填 | 编辑器 `task.data` |
| result | `Record<string, unknown>[] \| null` | `undefined` | 已有结果 |

### AnnotationCanvas Methods

| 名称 | 类型 | 说明 |
|------|------|------|
| getResult | `() => Record<string, unknown>[] \| null` | 当前标注结果 |
| undo | `() => void` | 标注历史后退一步 |
| redo | `() => void` | 标注历史前进一步 |
