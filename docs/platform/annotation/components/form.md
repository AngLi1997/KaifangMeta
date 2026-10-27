# 表单 Form

> [工作台组件](README.md) · 放在任意布局容器

按字段定义渲染的著录表单。字段名称、标签、类型、必填、选项都在模板里配置；值随标注结果保存，提交时校验必填。

## 与 Label Studio 控件的分工

两者都能录入文本、选项、数字、日期，按下表选，**能用 Label Studio 控件的优先用控件**：

| 场景 | 用 |
|------|----|
| 输入与图像区域、文本片段绑定（每个框一个值，`perRegion`） | Label Studio 控件（画布内） |
| 结果要参与 Label Studio 质检比对、训练回流 | Label Studio 控件 |
| 与区域无关的整条著录字段，需要放在画布之外、多列排版 | 表单 |
| 没有画布的纯著录模板 | 表单 |

两者也可组合：用控件画框，字段经 `bind` 自动回填，见[组件事件与框选回填](../linkage.md)（设计中）。

## 演示

### 基础用法

```xml
<Form name="meta" columns="2">
  <Field name="title" label="题名" type="text" required="true"/>
  <Field name="secret" label="密级" type="select" options="公开,内部,秘密"/>
  <Field name="date" label="成文日期" type="date"/>
  <Field name="pages" label="页数" type="number"/>
</Form>
```

### 全部字段类型

```xml
<Form name="all" columns="2">
  <Field name="a" label="文本" type="text"/>
  <Field name="b" label="数字" type="number"/>
  <Field name="c" label="下拉" type="select" options="公开,内部"/>
  <Field name="d" label="单选" type="radio" options="永久,定期"/>
  <Field name="e" label="多选" type="checkbox" options="重点,待补"/>
  <Field name="f" label="日期" type="date"/>
  <Field name="g" label="开关" type="switch"/>
  <Field name="h" label="多行文本" type="textarea"/>
</Form>
```

| type | 控件 | 值类型 |
|------|------|--------|
| `text` | 输入框 | `string` |
| `textarea` | 多行输入，占满整行 | `string` |
| `number` | 数字输入 | `number` |
| `select` | 下拉，可清空 | `string` |
| `radio` | 单选组 | `string` |
| `checkbox` | 多选组 | `string[]` |
| `date` | 日期选择 | `string`（`yyyy-MM-dd`） |
| `switch` | 开关 | `boolean` |

### 在设计器中配置

选中表单后，右侧「字段」逐条编辑标签、字段名、类型、必填与选项（逗号分隔），「添加字段」追加一条。

## 生命周期

| 阶段 | 时机 | 行为 |
|------|------|------|
| 初始化 | 工作台解析后、切换条目 | 从结果中 `type: km.form`、`from_name` 为本表单 `name` 的条目回填；没有则为空 |
| 编辑 | 用户输入 | 值写入工作台表单数据，「查看数据」即时可见 |
| 保存 | 保存命令 | 不校验，连同画布结果保存为草稿 |
| 提交 | 提交命令 | 校验必填，缺失时提示「请填写「字段标签」」并中止；通过后随结果提交 |

## 结果格式

```json
{ "type": "km.form", "from_name": "meta", "value": { "title": "关于开展档案数字化质量检查的通知", "secret": "内部", "tags": ["重点"] } }
```

## API

### Form 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | `string` | 自动编号 `form`、`form_2` | 表单名，快照与结果中的键，模板内唯一 |
| columns | `number` | `2` | 每行字段数，设计器中可选 1–4 |

### Field 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | `string` | 必填 | 字段名，表单内唯一 |
| label | `string` | — | 显示标签 |
| type | `'text' \| 'textarea' \| 'number' \| 'select' \| 'radio' \| 'checkbox' \| 'date' \| 'switch'` | `'text'` | 字段类型 |
| required | `boolean` | `false` | 提交时必填 |
| options | `string` | — | 选项，逗号分隔；`select`、`radio`、`checkbox` 使用 |
