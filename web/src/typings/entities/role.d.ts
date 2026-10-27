/// <reference path="../global.d.ts"/>

namespace Entity {
  interface Role {
    id: number
    name: string
    desc?: string
    /** system 只在系统租户生效，tenant 在绑定的租户内生效 */
    scope: 'system' | 'tenant'
    created_at?: string
  }

  type MenuType = 'catalog' | 'menu'

  interface Menu {
    id: number
    name: string
    path: string
    href?: string | null
    menu_type: MenuType
    icon?: string | null
    order: number
    parent_id: number
    is_hidden: boolean
    component: string
    keepalive: boolean
    redirect?: string | null
    children?: Menu[]
  }

  type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

  interface Api {
    id: number
    path: string
    method: HttpMethod
    summary: string
    tags: string
    created_at?: string
  }

  interface AuditLog {
    id: number
    user_id: number
    username: string
    tenant_id: string
    module: string
    summary: string
    method: string
    path: string
    status: number
    response_time: number
    request_args: unknown
    response_body: unknown
    created_at: string
  }
}
