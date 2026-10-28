/** 环境变量统一来自仓库根目录 .env（vite.config.ts 的 envDir） */
interface ImportMetaEnv {
  /** 项目基本地址 */
  readonly VITE_BASE_URL: string
  /** 项目标题 */
  readonly APP_TITLE: string
  /** 控制台 API 前缀（经网关） */
  readonly VITE_BASE_API: string
  /** 开发服务器端口 */
  readonly VITE_PORT: string
  /** 运维看板 HTTPS 反代端口 */
  readonly VITE_MINIO_CONSOLE_HTTPS_PORT?: string
  readonly VITE_APISIX_DASHBOARD_HTTPS_PORT?: string
  readonly VITE_ETCD_WORKBENCH_HTTPS_PORT?: string
  /** 是否开启打包压缩 */
  readonly VITE_BUILD_COMPRESS?: 'Y' | 'N'
  /** 压缩算法类型 */
  readonly VITE_COMPRESS_TYPE?:
    | 'gzip'
    | 'brotliCompress'
    | 'deflate'
    | 'deflateRaw'
  /** 路由模式 */
  readonly VITE_ROUTE_MODE?: 'hash' | 'web'
  /** 首次加载页面 */
  readonly VITE_HOME_PATH: string
  /** 版权信息 */
  readonly VITE_COPYRIGHT_INFO: string
  /** 默认语言 */
  readonly VITE_DEFAULT_LANG: App.lang
  /** 本地存储前缀 */
  readonly VITE_STORAGE_PREFIX: string
  /** 控制台 OIDC client_id（来自 CONSOLE_CLIENT_ID） */
  readonly CONSOLE_CLIENT_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
