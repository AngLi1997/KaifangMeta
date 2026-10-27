# 按钮 Button

> [工作台组件](README.md) · 只能放在[按钮栏](button-bar.md)里（拖到其他容器时自动包一层按钮栏）

触发工作台的公共命令。一个按钮对应一个动作，同一动作在模板里只放一次。

## 演示

### 基础用法

```xml
<ButtonBar>
  <Button action="undo"/>
  <Button action="redo"/>
  <Spacer/>
  <Button action="save"/>
  <Button action="submit"/>
</ButtonBar>
```

撤销、重做在左，`<Spacer/>` 把保存、提交推到右侧；设计器里拖动可改顺序或移到其他按钮栏。

### 查看与导出

```xml
<Button action="view-data"/>
<Button action="export"/>
```

「查看数据」打开抽屉，先看再导出；「导出」点击后选 JSON 或 YAML 直接下载。两者内容相同，文件名为 `{条目名}.json` / `.yaml`。

## 动作

| action | 文案 | 命令行为 | 发出事件 | 何时不可用 |
|--------|------|---------|---------|-----------|
| `undo` | 撤销 | 编辑器标注历史后退一步 | — | — |
| `redo` | 重做 | 编辑器标注历史前进一步 | — | — |
| `prev` | 上一份 | 切到上一条目 | `prev` | 没有上一份 |
| `next` | 下一份 | 切到下一条目 | `next` | 没有下一份 |
| `view-data` | 查看数据 | 打开快照抽屉 | — | — |
| `export` | 导出 | 下拉选 JSON / YAML，下载快照 | — | — |
| `log` | 日志 | 弹窗列出本次打开后的操作记录（保存、提交、导出等），按钮上显示条数；切换条目时清空 | — | — |
| `save` | 保存 | 取当前结果，保存草稿，条目状态不变 | `save(result)` | 加载中 |
| `submit` | 提交 / 提交并下一份 | 取当前结果提交，条目置为已标注 | `submit(result)` | 加载中 |

`open`、`ocr-box`、`layout-analysis` 在[工作台布局与插件](../layout.md)中已设计，随对应能力开放。

## 生命周期

按钮本身无状态：每次点击调用工作台命令 `run(action)`，命令执行后写一条日志，可用「日志」按钮查看。`preview` 模式下 `save`、`submit`、`prev`、`next` 只写日志。

## API

### Button 属性

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| action | `'undo' \| 'redo' \| 'prev' \| 'next' \| 'view-data' \| 'export' \| 'log' \| 'save' \| 'submit'` | 必填 | 动作 |

### 外观

| 动作 | 样式 |
|------|------|
| `submit` | 主色按钮 |
| `save` | 默认按钮 |
| 其他 | 无边框按钮 |

### 调用

宿主页面可不经按钮直接执行同一命令（导出用 `export-json` / `export-yaml`）：

```ts
workbenchRef.value?.run('save')
```

保存接口：

```http
POST /api/v1/annotation/item/save
Content-Type: application/json

{ "id": 1, "result": [], "draft": true }
```

`draft: true` 只保存结果；省略或为 `false` 时提交，条目置为已标注并更新工单进度。
