import { fetchUserApis, fetchUserInfo, getToken, logout } from '@/service'
import { useRouteStore } from './router'
import { useTabStore } from './tab'

interface AuthStatus {
  userInfo: Api.Login.Info | null
  /** 接口权限码（method + path），用于按钮权限 */
  permissions: string[]
}

export const useAuthStore = defineStore('auth-store', {
  state: (): AuthStatus => ({
    userInfo: null,
    permissions: [],
  }),
  getters: {
    /** Token 只在内存中，存在即已登录 */
    isLogin: () => Boolean(getToken()),
    isSuperUser: state => Boolean(state.userInfo?.is_superuser),
    isSystemTenant: state => Boolean(state.userInfo?.is_system_tenant),
  },
  actions: {
    /** 加载当前用户与接口权限（路由初始化前调用） */
    async loadUser() {
      const [info, apis] = await Promise.all([fetchUserInfo(), fetchUserApis()])
      if (!info.isSuccess || !apis.isSuccess)
        throw new Error('加载用户信息失败')
      this.userInfo = info.data
      this.permissions = apis.data
    },
    /** 退出：清空本地状态后跳转认证模块吊销会话 */
    async logout() {
      useRouteStore().resetRouteStore()
      useTabStore().clearAllTabs()
      this.$reset()
      logout()
    },
  },
})
