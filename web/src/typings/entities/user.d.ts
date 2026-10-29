/// <reference path="../global.d.ts"/>

namespace Entity {
  /** 控制台本地用户 */
  interface User {
    id?: number
    /** 身份账号 sub（认证模块签发，全局唯一） */
    sub?: string
    username?: string
    alias?: string | null
    email?: string
    phone?: string | null
    is_active?: boolean
    is_superuser?: boolean
    last_login?: string | null
    created_at?: string
    updated_at?: string
  }

  /** 认证模块的身份账号（只含基础字段） */
  interface Account {
    sub: string
    tenant_id: string
    tenant_name?: string
    member_tenants?: Pick<Tenant, 'id' | 'name'>[]
    username: string
    email: string | null
    name: string | null
    phone: string | null
    org_id: number | null
    org_name?: string | null
    status: 'active' | 'disabled'
    created_at: string
  }

  /** 身份账号列表中的控制台成员信息，按 sub 关联 */
  interface IdentityAccount extends Account {
    console_member: ConsoleMember | null
  }

  interface AccountForm {
    tenant_id: string
    username: string
    email: string | null
    name: string | null
    phone: string | null
    password?: string | null
    status: 'active' | 'disabled'
    member_tenant_ids?: string[]
    org_id: number | null
  }

  /** 认证模块的机构（按租户维护的机构树） */
  interface Org {
    id: number
    parent_id: number | null
    code: string
    name: string
    level: number
    sort_order: number
    status: 'active' | 'disabled'
    account_count?: number
    children?: Org[]
  }

  interface Tenant {
    id: string
    name: string
    status: 'active' | 'disabled'
    created_at: string
  }

  interface ConsoleMember {
    sub: string
    roles: (Pick<Role, 'id' | 'name'> & { tenant_id: string })[]
    is_superuser: boolean
    is_active: boolean
    last_login: string | null
  }

  /** 接入应用（认证模块 iam.client） */
  interface AppRoute {
    path: string
    nodes: string[]
    health: string | null
  }

  interface AppGateway {
    prefix: string
    routes: AppRoute[]
    public_paths: string[]
    rate_limit: number
  }

  interface AppPortal {
    entry?: string | null
    icon?: string | null
    description?: string | null
    order?: number
  }

  interface App {
    client_id: string
    name: string
    type: 'web' | 'service' | 'desktop'
    owner: string | null
    status: 'online' | 'disabled'
    tenants: string[]
    tenant_names?: string[]
    scopes: string[]
    redirect_uris: string[]
    post_logout_redirect_uris: string[]
    gateway: AppGateway | Record<string, never>
    portal: AppPortal
    sync_status: 'synced' | 'pending' | null
    gateway_state?: 'synced' | 'pending' | 'drift' | null
    instances?: { healthy: number, total: number } | null
    synced_at: string | null
    created_at: string
  }

  interface AppSecrets {
    client_secret?: string
    gateway_secret?: string
  }
}
