# 对象存储路径

> 平台基础设施 · MinIO。相关：[多应用设计](apps.md)、[业务与平台通信](communication.md)、[网关与鉴权](gateway.md)、[定时任务与异步处理](platform/scheduler.md)。

## 要点

- **单桶**：平台所有对象放在一个私有桶 `kaifang-meta-platform`（`.env` 中 `MINIO_BUCKET`），不按模块建桶。
- **一个业务一个一级目录**：路径统一为 `{业务目录}/{tenant_id}/{归属}/…`，业务目录在下文登记表中唯一登记。
- **租户紧跟业务目录**：共享部署下按租户隔离与清理；与租户无关的对象（如安装包）用系统租户 `t_system`。
- **保留期按业务目录配置**：MinIO 生命周期规则以业务目录为前缀，一个目录一条规则。
- **路径由平台生成**：业务系统经平台接口申请预签名 URL，不能指定任意路径；接口与事件只传对象路径。
- **新业务先登记再使用**：新增业务目录须先补充本文登记表，未登记的前缀不允许写入。

## 路径规则

```text
kaifang-meta-platform/{业务目录}/{tenant_id}/{归属}/{业务自定义层级}/{文件名}
```

| 段 | 规则 | 示例 |
|----|------|------|
| 业务目录 | 小写字母与 `-`，与平台模块或业务名对应，登记后不改名 | `capability` |
| `tenant_id` | Token 中的 `tid`；租户无关对象用 `t_system` | `t_5e2a9c1d7b3f4086` |
| 归属 | 调用方 `client_id`、应用空间、连接器或设备；用于校验对象属于调用方 | `kaifang-meta-archive-room` |
| 业务自定义层级 | 由该业务在登记表中约定，含可确定的 ID（任务 ID、批次号等），重试覆盖不追加 | `runs/{run_id}/input` |
| 文件名 | 保留原始扩展名；用户上传的文件名不直接作为路径，改用 ID 或档号 | `0012.pdf` |

## 业务目录登记表

| 业务目录 | 所属模块 | 路径 | 内容 | 保留 |
|----------|----------|------|------|------|
| `console` | 平台控制台 | `console/{tenant_id}/avatars/{sub}` | 用户头像 | 随用户删除 |
| `capability` | 能力 | `capability/{tenant_id}/{client_id}/runs/{run_id}/input/…`、`…/output/…` | 能力调用的输入副本与大结果 | 运行结束后 30 天 |
| `annotation` | 数据标注 | `annotation/{tenant_id}/{client_id}/tasks/{task_id}/manifest/{part_no}.jsonl.gz` | 清单分片 | 建单后 7 天 |
| | | `annotation/{tenant_id}/{client_id}/tasks/{task_id}/files/…` | 副本模式的送标注文件 | 业务 `ack` 后 90 天 |
| | | `annotation/{tenant_id}/{client_id}/tasks/{task_id}/{pages,tiles,media}/{item_key}/…` | 预处理派生文件（页图、瓦片、转码） | 业务 `ack` 后 90 天 |
| | | `annotation/{tenant_id}/{client_id}/tasks/{task_id}/exports/v{ver}.jsonl.gz` | 结果导出 | 业务 `ack` 后 90 天 |
| `ai` | AI | `ai/{tenant_id}/{space}/kb/{kb}/docs/{external_id}/…` | 知识库文本副本（WeKnora 写入；全文库只存文本，不存原件） | 随文档删除 |
| `ingest` | 数据采集 | `ingest/{tenant_id}/{connector或device}/{yyyy/mm/dd}/…` | 采集原始区 | 按连接器配置 |
| `jobs` | 任务调度 | `jobs/{tenant_id}/{job_id}/{step}/{item_key}` | 流水线步骤的大结果 | 任务结束后 30 天 |
| `release` | 客户端发布 | `release/t_system/{client_id}/{version}/{platform}/…` | 客户端安装包（`kaifang-harness`） | 版本下线后删除 |

## 新增业务目录

1. 在上表新增一行：业务目录、所属模块、路径模板、内容、保留期；路径必须满足「路径规则」。
2. 在对应模块文档中引用本文，不在模块文档里另写路径规则。
3. 按保留期添加生命周期规则：

```bash
mc ilm rule add --prefix "capability/" --expire-days 30 local/kaifang-meta-platform
```

4. 代码中用该模块的路径构造函数生成对象名，不在调用处拼接字符串。

## 访问规则

- 桶策略私有、无匿名访问；只有平台服务账号持有 MinIO 凭据，Worker、算子节点各用最小权限账号（按业务目录前缀授权）。
- 上传：业务后端调用平台接口申请上传 URL，平台按调用方 `client_id` 与 `tid` 生成路径并签发（15 分钟有效）；下载同理，平台校验对象属于调用方后签发。
- 业务系统自己的原件存放在业务自己的对象存储，不进入本桶；部署上共用 MinIO 集群时也必须是独立的桶与账号，见 [多应用设计](apps.md)。

## 示例：一份档案扫描件的存放位置

| 阶段 | 位置 |
|------|------|
| 档案员上传原件 | 智慧档案室对象存储 `archive-files/{tenant}/{batch}/{doc_no}.pdf` |
| 送解析 | 复制到 `capability/{tenant}/kaifang-meta-archive-room/runs/{run_id}/input/` |
| 预抽取结果 | 平台 `capability` schema（小结果）/ `capability/…/output/`（大结果）→ 业务拉回存业务库 |
| 送标注 | 默认引用模式：原件留在档案室存储，平台只存清单分片 `annotation/{tenant}/kaifang-meta-archive-room/tasks/{task_id}/manifest/` 与页图 `…/pages/`；标注员浏览器经平台 302 直接从档案室存储取文件 |
| 回写确认 | 著录版本写业务库；`ack` 后平台副本进入保留期 |
| 全文入库 | 业务推送到 `ai/{tenant}/space.archive-room/kb/archive-fulltext/…`，带 ACL 元数据 |
