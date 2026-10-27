import { createAlovaInstance } from './alova'

// 控制台 API 一律经网关（模式 A）：/kaifang-meta/console/api/v1
export const request = createAlovaInstance({
  baseURL: import.meta.env.VITE_BASE_API,
})
