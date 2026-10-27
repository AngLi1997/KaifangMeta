# 数据采集

> 平台 · 采集模块 + 独立进程 `kaifang-meta-edge-agent × N`（部署在现场，对接硬件）。

- 中心侧插件式连接器：数据库（含 CDC 增量）、对象存储、FTP / 文件、HTTP API。
- 统一落地原始区（MinIO + 元数据），校验后发出事件。
- 硬件只由 kaifang-meta-edge-agent 对接：设备驱动、本地缓存、断点续传。
- 不引入 MQTT Broker：edge-agent 以自己的 client credentials 换 Service Token，经网关 HTTPS 批量上报（`POST /kaifang-meta/platform/ingestion/v1/telemetry`，按「设备 + 序号」幂等）；文件类数据走 MinIO 预签名 URL 直传。
- 下发指令由 edge-agent 长轮询拉取（`GET …/commands?wait=30s`），平台不反向连接现场；断网期间数据缓存在本地，恢复后按序号续传。
