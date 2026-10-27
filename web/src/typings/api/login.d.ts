/// <reference path="../global.d.ts"/>

namespace Api {
  namespace Login {
    /** /base/userinfo：控制台本地用户（按 sub 关联认证模块的身份账号） */
    interface Info extends Entity.User {
      id: number
      avatar?: string
      tenant_id: string
      /** 系统租户持有 system 范围，可跨租户管理 */
      is_system_tenant: boolean
      /** 可切换的租户 */
      tenants: Pick<Entity.Tenant, 'id' | 'name'>[]
    }
  }
}
