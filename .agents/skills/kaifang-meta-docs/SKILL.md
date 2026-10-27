---
name: kaifang-meta-docs
description: kaifang-meta 中台设计文档仓库的写作与维护规范：文档结构、模块划分、命名约定、代码块写法、README 目录同步、文档与设计 / 原型 / 架构图的一致性，以及 prototype.html 的界面约定。只要在本仓库新增、修改、移动或删除任何文档（docs/**/*.md、README.md），改动架构设计、工作流、路由，或编辑 docs/design/ 下的架构图和原型，都应先使用本 skill，即使用户没有明确提到"规范"。
---

# kaifang-meta 文档规范

本仓库是设计文档仓库，文档就是交付物。下面的规则让读者能快速找到结论，也让文档、架构图、原型三者不互相矛盾。

## 文档结构

- **按模块划分**：一个模块（或一个跨部署段主题）一份文档，平台模块放 `docs/platform/<模块>/`。不写跨模块的大杂烩文档，相关内容用相对链接互引，不用节号（节号一改就全错）。
- **结构固定**：标题 → 一行引用说明所属部署段 / 模块与相关文档 → 「要点」（3–7 条结论）→ 详细设计。读者只看要点就该知道结论。
- **简洁易读**：先结论后理由；能用表格就不用长段落；不写与设计无关的背景铺垫。
- **代码 / 命令清晰**：放在带语言标注的代码块（`bash`、`yaml`、`json`、`http` 等）中，可直接复制执行；接口写全方法与路径，示例值用明显的示例数据。

示例开头：

```markdown
# 数据采集

> 平台 · 采集模块 + 独立进程 `kaifang-meta-edge-agent × N`。相关：[定时任务](scheduler.md)。

## 要点

- 中心侧插件式连接器：数据库、对象存储、FTP / 文件、HTTP API。
- ……
```

## 保持一致

- **新增 / 移动 / 删除文档**：同步更新 `README.md` 文档目录（作用 + 主要内容各一句，按模块分组）。
- **功能或设计修改后**：同步更新对应模块文档、架构图 `docs/design/architecture.html` 和原型 `docs/design/prototype.html`。`docs/prototype.md` 的路由表必须与原型中的路由一致。
- **发现不一致时先停下问用户**：文档与实现（或文档之间、文档与原型之间）不一致时，向用户说明差异并确认是改文档还是改实现，不要自行择一修改——哪边是"对的"只有用户知道。

## 写作约定

- 文档与界面文案均使用简体中文。
- 命名统一以 `kaifang-meta` 为前缀：部署进程、镜像、SDK 包名、应用 client_id 用 `kaifang-meta-*`，网关路由用 `/kaifang-meta/*`，界面品牌标识为 `KM`。新增名称沿用此约定。
- 唯一例外：Agent 桌面端项目名为 `kaifang-harness`（client_id、安装包同名，下载主页路由 `/kaifang-meta/harness/`）。

## 界面（原型 / 架构图）

- 避免不必要的辅助标签和说明，让布局本身发挥说明作用。
- 设计语言统一为 nova-admin 风格（与控制台前端 `web/` 一致），布局与组件形态见 skill [kaifang-meta-ui](../kaifang-meta-ui/SKILL.md)。
- 编辑 `docs/design/prototype.html` 前先读 [references/prototype.md](references/prototype.md)（路由、外壳、模板助手、配色）。
- 架构图 `docs/design/architecture.html` 是纯 HTML/CSS（无 JS），上中下结构：接入端 → [独立进程 | 网关 + 平台模块 | 业务系统] → 平台基础设施，用颜色块与带标注箭头表示角色与调用方向。

预览：

```bash
open docs/design/prototype.html#ar-import
```
