/// <reference path="../global.d.ts"/>

namespace Api {
  namespace Portal {
    interface App {
      client_id: string
      name: string
      type: string
      status: 'online' | 'disabled'
      entry: string
      icon?: string
      description?: string
    }
    /** /portal/apps：当前用户在当前租户下可进入的应用 */
    interface Info {
      user: { username: string, name?: string, avatar?: string }
      tenant_id: string
      tenants: Pick<Entity.Tenant, 'id' | 'name'>[]
      apps: App[]
    }
  }
}
