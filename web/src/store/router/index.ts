import type { MenuOption } from 'naive-ui'
import { router } from '@/router'
import { fetchUserMenus } from '@/service'
import { useAuthStore } from '@/store/auth'
import { $t, message } from '@/utils'
import { createMenus, createRoutes, generateCacheRoutes } from './helper'
import { menusToRoutes } from './menus'

interface RoutesStatus {
  isInitAuthRoute: boolean
  menus: MenuOption[]
  rowRoutes: AppRoute.RowRoute[]
  activeMenu: string | null
  cacheRoutes: string[]
}
export const useRouteStore = defineStore('route-store', {
  state: (): RoutesStatus => {
    return {
      isInitAuthRoute: false,
      activeMenu: null,
      menus: [],
      rowRoutes: [],
      cacheRoutes: [],
    }
  },
  actions: {
    resetRouteStore() {
      this.resetRoutes()
      this.$reset()
    },
    resetRoutes() {
      if (router.hasRoute('appRoot'))
        router.removeRoute('appRoot')
    },
    // set the currently highlighted menu key
    setActiveMenu(key: string) {
      this.activeMenu = key
    },

    /** 动态路由：菜单由后端按角色返回，前端只做结构转换 */
    async initRouteInfo() {
      await useAuthStore().loadUser()
      const result = await fetchUserMenus()
      if (!result.isSuccess || !result.data)
        throw new Error('Failed to fetch user menus')
      return menusToRoutes(result.data)
    },
    async initAuthRoute() {
      this.isInitAuthRoute = false

      try {
        // Initialize route information
        const rowRoutes = await this.initRouteInfo()
        if (!rowRoutes) {
          const error = new Error('Failed to get route information')
          message.error($t(`app.getRouteError`))
          throw error
        }
        this.rowRoutes = rowRoutes

        // Generate actual route and insert
        const routes = createRoutes(rowRoutes)
        router.addRoute(routes)

        // Generate side menu
        this.menus = createMenus(rowRoutes)

        // Generate the route cache
        this.cacheRoutes = generateCacheRoutes(rowRoutes)

        this.isInitAuthRoute = true
      }
      catch (error) {
        // 重置状态并重新抛出错误
        this.isInitAuthRoute = false
        throw error
      }
    },
  },
})
