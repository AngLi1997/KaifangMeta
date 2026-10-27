# 工作台组件

> 平台 · 数据标注模块。标注工作台可拖拽组件的使用说明，按组件分篇。设计背景见[工作台布局与插件](../layout.md)。

## 要点

- 工作台默认空白，用布局容器（网格、列表、面板）搭出界面，再放入组件；容器可任意嵌套。
- 组件写在模板 XML 里（`<Workbench>` 根），也可以在「场景模板 → 布局」里拖拽摆放，两种方式改的是同一份 XML。
- 组件由平台内置，模板只能引用、配置，不能写脚本。
- 旧模板（根为 `<View>`）不用改，按默认布局（工具栏 + 画布 + 状态栏）渲染。

## 快速上手

### 在模板里使用

```xml
<Workbench>
  <ButtonBar>
    <Button action="undo"/>
    <Button action="redo"/>
    <Spacer/>
    <Button action="save"/>
    <Button action="submit"/>
  </ButtonBar>
  <Grid columns="2">
    <Panel title="档案详情">
      <Form name="meta">
        <Field name="title" label="题名" type="text" required="true"/>
      </Form>
    </Panel>
    <Panel title="内容">
      <Canvas>
        <View>
          <Image name="image" value="$image"/>
        </View>
      </Canvas>
    </Panel>
  </Grid>
</Workbench>
```

### 在页面里使用

工作台与设计器都在 `web/src/components/custom/workbench/`：

```vue
<script setup lang="ts">
import Workbench from '@/components/custom/workbench/Workbench.vue'
</script>

<template>
  <Workbench
    :config="task.config"
    :data="item.data"
    :result="item.result"
    :item="{ id: item.id, name: item.name, index, total }"
    :has-prev="!!prevId"
    :has-next="!!nextId"
    @save="result => save(result, true)"
    @submit="result => save(result, false)"
    @prev="load(prevId)"
    @next="load(nextId)"
  />
</template>
```

## 组件

组件库分组与设计器左侧一致：

| 分组 | 组件 | 标签 | 职责 | 放在 | 文档 |
|------|------|------|------|------|------|
| — | 工作台 | `<Workbench>` | 根；纵向排列子节点，提供数据与命令 | — | [workbench.md](workbench.md) |
| 布局 | 网格 | `<Grid>` | 二维排布，跨行跨列 | 任意容器 | [grid.md](grid.md) |
| 布局 | 列表 | `<List direction>` | 一维排布，按占比分配 | 任意容器 | [list.md](list.md) |
| 布局 | 面板 | `<Panel>` | 标题 + 边框 + 滚动 | 任意容器 | [panel.md](panel.md) |
| 布局 | 间隔 | `<Spacer>` | 按钮栏里推开两组按钮；其他容器里留一段空白 | 任意容器 | [spacer.md](spacer.md) |
| 组件 | 表单 | `<Form>` + `<Field>` | 画布之外的著录字段 | 任意容器 | [form.md](form.md) |
| 组件 | 数据表格 | `<DataTable>` + `<Column>` | 只读行数据（当前为样例） | 任意容器 | [data-table.md](data-table.md) |
| 按钮 | 按钮栏 | `<ButtonBar>` | 横向排列按钮并对齐 | 任意容器 | [button-bar.md](button-bar.md) |
| 按钮 | 按钮 | `<Button action>` | 触发公共命令 | 按钮栏 | [button.md](button.md) |
| Label Studio | 画布 | `<Canvas>` | 承载编辑器 | 任意容器，最多一个 | [canvas.md](canvas.md) |
| Label Studio 对象 / 控件 / 视觉 | 原生标签 | `<Image>`、`<RectangleLabels>`… | 标注对象与控件 | 画布 | [canvas.md](canvas.md) |
| 工具 | 布局设计器 | `LayoutDesigner` | 拖拽编辑模板 | 场景模板页 | [designer.md](designer.md) |

## 分工与去重

每个组件只做一件事；功能相近时按下表选择。与 Label Studio 能力重叠时，优先用 Label Studio。

| 容易混淆 | 区别 | 怎么选 |
|----------|------|--------|
| 网格 / 列表 | 网格是二维（行列、跨行跨列）；列表是一维（按占比） | 左右分栏、跨行跨列用网格；一列上下或左右按比例排开用列表 |
| 列表 / 面板 | 面板带标题、边框，内容超出时滚动；列表无外观 | 需要标题或独立滚动区时用面板 |
| 按钮栏 / 横向列表 | 按钮栏只放按钮与间隔，有对齐方式；列表只放容器与组件 | 工具栏、状态栏用按钮栏 |
| 间隔 / 按钮栏对齐 | 间隔把按钮分成左右两组；对齐方式作用于整栏 | 整栏同向用 `align`，左右两组用间隔 |
| 查看数据 / 导出 | 查看数据先看再导出；导出直接下载 | 都是同一份快照，按需放一个或两个 |
| 表单 / Label Studio 控件 | 控件在画布内，可与区域绑定、参与质检比对；表单在画布外 | 优先 Label Studio 控件；与区域无关的整条著录字段或无画布模板用表单（见[表单](form.md#与-label-studio-控件的分工)） |
| 面板标题 / `Header` | 面板标题在画布外；`Header` 是画布内文字 | 画布内用 `Header` |
| 图像缩放、旋转 | 编辑器自带缩放平移，`Image` 有 `zoomControl`、`rotateControl` | 用 Label Studio，不做平台组件 |
| `Rectangle` / `RectangleLabels` | 前者框选不带标签（如 OCR 框选），后者带标签 | 需要分类时用 `RectangleLabels` |

本次整理的变化：

| 原来 | 现在 |
|------|------|
| 按钮、状态项可放进任意容器，横向列表兼作工具栏 | 按钮只能放进按钮栏（拖到其他容器时自动包一层）；列表只排容器与组件 |
| 状态项「当前条目」「条目状态」「日志」 | 移除前两项；日志改为按钮，点击弹窗查看 |
| 弹性间隔 | 改名「间隔」，归入布局分组：按钮栏里占满剩余宽度，其他容器里是一段 16px 空白（可设占比） |
| 「导出 JSON」「导出 YAML」两个按钮 | 合并为「导出」，点击选格式 |
| 画布在「组件」分组 | 移到「Label Studio」分组 |
| 网格子节点只能跨列（`span`） | `colSpan`、`rowSpan`；网格可设固定行数 `rows` |
| 设计中的图像动作栏（旋转、缩放） | 不实现，用 Label Studio 自带 |

## 通用约定

| 项 | 约定 |
|----|------|
| 放置 | 布局容器、表单、数据表格、按钮栏、画布放进工作台根或任意容器；按钮只放按钮栏，间隔可放任意容器；Label Studio 标签只放画布；放错位置时设计器不接收，手写 XML 保存时报错 |
| 唯一性 | 同一个按钮动作、画布在一个模板里只放一次；其余可以重复，表单与表格的 `name` 不重复 |
| 尺寸 | 默认撑满：列表里按钮栏按内容高度，其他子节点平分剩余空间，`size`（常用值或手动输入 1%–100%）指定占比，横向列表也可用 `columns` 等分；网格子节点撑满单元格，`colSpan` / `rowSpan` 跨列跨行 |
| 命令 | 按钮触发的都是工作台命令，宿主页面也可以用 `run(action)` 调用同一个命令 |
| 数据 | 组件不保存状态：表单值随标注结果保存，界面上能看到的数据都在工作台快照里，可查看、导出 |
| 联动 | 组件之间暂无可配置联动；`<Link>` 见[工作台布局与插件 · 组件联动](../layout.md#组件联动) |
