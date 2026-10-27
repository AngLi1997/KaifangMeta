import { useAuthStore } from '@/store'
import { isArray } from 'radash'

/**
 * 按钮 / 操作权限：权限码为「小写方法 + 接口路径」，如 post/api/v1/role/create（后端 /base/userapi）
 * 超级管理员拥有全部权限；传入数组时满足任一即可。
 */
export function usePermission() {
  const authStore = useAuthStore()

  function hasPermission(permission?: string | string[]) {
    if (!permission)
      return true
    if (authStore.isSuperUser)
      return true
    const codes = isArray(permission) ? permission : [permission]
    return codes.some(code => authStore.permissions.includes(code))
  }

  return { hasPermission }
}
