# 场景模板

> 平台 · 数据标注模块。标注界面如何自定义、场景模板如何定义与发布。相关：[数据标注](overview.md)、[Label Studio 集成与语言](labelstudio.md)。

## 要点

- **模板 = 编辑器 XML + 数据契约 + 参数 + 预标注映射 + 结果映射 + 质检规则 + 训练回流**，一个 YAML 描述。
- **界面自定义靠 Label Studio XML + 工作台布局**：画布能力上限即编辑器能力；根标签用 `<Workbench>` 可用网格、列表、面板自由搭建布局并放入平台组件（表单、数据表格等），见[工作台布局与插件](layout.md)；不开放自定义 JS。
- **三级归属**：系统模板（平台维护）、租户模板（租户内共享）、应用模板（业务应用登记，只对本应用可见）。
- **不可变版本**：每次发布生成 `code@version`，工单引用具体版本，后续修改不影响已建工单。
- **业务拿字段不拿坐标**：结果映射把标注 JSON 转成「字段 → 值」；框选、实体等原始结果另附 `raw`。

## 模板组成

```yaml
code: archive.ws-item            # 模板编码，版本号由平台递增
name: 文书著录要素校对
scope: tenant                    # system | tenant | app
modality: document               # image | text | document | video | audio | qa
data_schema:                     # 条目 data 的契约，导入时校验
  pages: { type: file[], mime: [image/*, application/pdf] }
  ocr_text: { type: string, required: false }
params:                          # 建单时可覆盖，替换 XML 中的 {{…}}
  secret_levels: [公开, 内部, 秘密]
editor: |                        # Label Studio 模板 XML
  <View>
    <Image name="page" valueList="$pages"/>
    <Header value="题名"/>
    <TextArea name="title" toName="page" editable="true" maxSubmissions="1"/>
    <Header value="文号"/>
    <TextArea name="doc_no" toName="page" editable="true" maxSubmissions="1"/>
    <Choices name="secret" toName="page" choice="single">
      {{#secret_levels}}<Choice value="{{.}}"/>{{/secret_levels}}
    </Choices>
  </View>
prediction_mapping:              # 清单 predictions → 编辑器 predictions
  title: { from_name: title, type: textarea }
  doc_no: { from_name: doc_no, type: textarea }
result_mapping:                  # 标注 JSON → 结果条目 fields
  title: textarea:title
  doc_no: textarea:doc_no
  secret_level: choices:secret
qa:
  default_policy: { sample_rate: 0.2, pass_rate: 0.98 }
  compare: field_exact           # field_exact | iou(0.8) | label_set
training:
  allowed: true
  dataset: extract.doc
```

| 部分 | 作用 |
|------|------|
| `data_schema` | 清单导入与自由标注上传时校验字段与文件类型，不合格的行记错误 |
| `editor` | Label Studio XML，或以 `<Workbench>` 为根、内含 `<Canvas><View>…</View></Canvas>` 的布局 XML，见[工作台布局与插件](layout.md) |
| `params` | 同一模板服务不同业务，如标签候选项、密级列表；建单时传 `template_params`，渲染后随数据集版本冻结 |
| `prediction_mapping` | 业务送来的预抽取 / 模型结果转成编辑器 predictions，标注员只确认或修改 |
| `result_mapping` | 业务直接拿字段值；未映射的模板（如目标检测）结果只有 `raw` |
| `qa.compare` | 抽检、交叉标注时的一致性算法 |
| `training` | 是否允许回流以及进入哪个训练数据集 |

## 内置场景库

| 场景 | 模态 | 编辑器要点 | 典型业务 |
|------|------|-----------|----------|
| 著录要素校对 | 文档（多页图像） | `Image valueList` + `TextArea` / `Choices`，带预抽取 | 智慧档案室导入 |
| OCR 文本校对 | 文档 | `Image` + `Rectangle` + `TextArea perRegion` | 识别训练集 |
| 版面要素框选 | 图像 | `RectangleLabels`（印章、签名、标题、表格） | 版面分析模型 |
| 目标检测 / 分割 | 图像 | `RectangleLabels` / `PolygonLabels` / `KeyPointLabels` | 库房设备、图像巡检 |
| 文本分类 | 文本 | `Choices` | 文书分类、密级判定 |
| 实体与关系 | 文本 | `Labels` + `Relations` | 知识抽取 |
| 视频分段与跟踪 | 视频 | `TimelineLabels`、`VideoRectangle` | 监控、库房视频 |
| 音频转写 | 音频 | `Audio` + `Labels` + `TextArea perRegion` | 会议录音 |
| 问答评测 | 文本 | `Text` + `TextArea` + `Rating` | 知识库评测集，见 [WeKnora](../capability/weknora.md) |
| 空白模板 | 任意 | 只有 `<View/>` | 自由标注时临时写 XML |

## 自定义与发布

| 谁 | 能做什么 |
|----|---------|
| 平台超级管理员 | 维护系统模板与内置场景库 |
| 租户管理员 / 标注管理员（`annotation:manage`） | 复制系统模板或新建租户模板，发布、停用 |
| 业务应用（Service Token） | `POST /templates` 登记应用模板，只对本应用可见 |
| 标注员（自由标注） | 用已发布模板，或在自己的自由标注任务里用空白模板写 XML；该 XML 只属于这个任务，不进模板库，可「另存为模板」交管理员发布 |

模板编辑器（控制台「场景模板」）：

- 独立页面「模板编辑」：标题旁按钮组切换「XML / 布局 / 预览」，前两者编辑同一份模板，布局为拖拽设计器（见[工作台布局与插件](layout.md)）；左侧模板信息与 XML 代码编辑器（语法高亮，按 Label Studio 标签 / 属性 / 可选值补全）；右侧同一个 `AnnotationCanvas` 用样例数据渲染并铺满预览区（窄于工作台最小宽度时整体等比缩小，内容超出时滚动），XML 不合法时只提示错误。
- 保存前校验：XML 能被编辑器解析；`toName` 指向存在的对象标签；`data_schema` 覆盖 XML 中的 `$变量`；`result_mapping` 引用的 `from_name` 存在。
- 发布生成不可变版本；停用的版本不能再建单，历史工单正常打开。

模板接口（前缀 `/kaifang-meta/platform/annotation/v1`）：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates?scope=&modality=` | 查询可用模板 |
| `GET` | `/templates/{code}/versions/{ver}` | 模板版本详情 |
| `POST` | `/templates` | 登记应用模板（业务）或租户模板（控制台） |
| `POST` | `/templates/{code}/versions` | 发布新版本 |
| `POST` | `/templates/{code}/versions/{ver}:disable` | 停用版本 |
