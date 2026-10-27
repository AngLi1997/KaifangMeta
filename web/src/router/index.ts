import type { App } from 'vue'
import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import { setupRouterGuard } from './guard'
import { routes } from './routes.inner'

const { VITE_ROUTE_MODE = 'hash', VITE_BASE_URL } = import.meta.env
export const router = createRouter({
  history: VITE_ROUTE_MODE === 'hash' ? createWebHashHistory(VITE_BASE_URL) : createWebHistory(VITE_BASE_URL),
  routes,
})
// 安装vue路由
export async function installRouter(app: App) {
  // 添加路由守卫
  setupRouterGuard(router)
  app.use(router)
  // 未登录时首次导航被守卫中止（整页跳转认证模块），不视为错误
  await router.isReady().catch(() => {}) // https://router.vuejs.org/zh/api/index.html#isready
}
