import type { Router } from 'vue-router'
import { getToken, startLogin } from '@/service'
import { useAppStore, useRouteStore, useTabStore } from '@/store'

const title = import.meta.env.APP_TITLE

export function setupRouterGuard(router: Router) {
  const appStore = useAppStore()
  const routeStore = useRouteStore()
  const tabStore = useTabStore()

  router.beforeEach(async (to, from, next) => {
    // 开始 loadingBar
    appStore.showProgress && window.$loadingBar?.start()

    // OIDC 回调等公开页面直接放行
    if (to.meta.requiresAuth === false) {
      next()
      return
    }

    // Token 只在内存：没有则跳转认证模块（prompt=none 静默恢复，SSO 失效才出登录页）
    if (!getToken()) {
      await startLogin({ returnTo: to.fullPath })
      next(false)
      return
    }

    // 根路由重定向到首页
    if (to.name === 'root') {
      next({ path: import.meta.env.VITE_HOME_PATH, replace: true })
      return
    }

    // 首次进入：加载用户、权限与动态路由
    if (!routeStore.isInitAuthRoute) {
      try {
        await routeStore.initAuthRoute()
      }
      catch {
        // 401 已由请求层续期 / 重新登录；其余错误（如 403 未开通）停留并提示
        next(false)
        return
      }
      // 动态路由加载完成后重新匹配当前地址，否则会落到 404
      next({ path: to.fullPath, replace: true, query: to.query, hash: to.hash })
      return
    }

    next()
  })
  router.beforeResolve((to) => {
    // 设置菜单高亮
    routeStore.setActiveMenu(to.meta.activeMenu ?? to.fullPath)
    // 添加tabs
    tabStore.addTab(to)
    // 设置高亮标签;
    tabStore.setCurrentTab(to.fullPath as string)
  })

  router.afterEach((to) => {
    // 修改网页标题
    document.title = `${to.meta.title} - ${title}`
    // 结束 loadingBar
    appStore.showProgress && window.$loadingBar?.finish()
  })
}
