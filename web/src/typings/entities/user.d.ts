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
}
