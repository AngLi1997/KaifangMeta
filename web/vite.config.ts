import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import { createVitePlugins } from './build/plugins'

// 配置统一来自仓库根目录 .env（单一配置入口）
const envDir = resolve(__dirname, '..')

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, '')

  return {
    envDir,
    // 浏览器只拿到 VITE_*、应用名与控制台 client_id，密钥类配置不暴露
    envPrefix: ['VITE_', 'APP_TITLE', 'CONSOLE_CLIENT_ID'],
    base: env.VITE_BASE_URL,
    plugins: createVitePlugins(env as unknown as ImportMetaEnv),
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT),
      strictPort: true,
      https: env.VITE_HTTPS === 'true'
        ? {
            cert: readFileSync(resolve(envDir, '.certs/kaifang-meta.crt')),
            key: readFileSync(resolve(envDir, '.certs/kaifang-meta.key')),
          }
        : undefined,
      proxy: {
        // 预签名文件地址只含路径，同源转发到 MinIO；Host 改为 MINIO_ENDPOINT 才能通过签名校验
        [`/${env.MINIO_BUCKET}/`]: {
          target: `${env.MINIO_SECURE === 'true' ? 'https' : 'http'}://${env.MINIO_ENDPOINT}`,
          changeOrigin: true,
        },
        // 认证与控制台 API 均经 APISIX（模式 A），与生产链路一致
        // xfwd 带上 X-Forwarded-Proto，认证模块据此决定 SSO Cookie 是否 Secure
        '/kaifang-meta': { target: `http://127.0.0.1:${env.APISIX_HTTP_PORT}`, xfwd: true },
      },
    },
    build: {
      target: 'esnext',
      reportCompressedSize: false, // 启用/禁用 gzip 压缩大小报告
    },
    optimizeDeps: {
      include: ['echarts'],
    },
  }
})
