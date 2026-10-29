import { request } from '../http'

interface Page { page?: number, page_size?: number }
type Ok = Service.ResponseResult<null>

// 控制台成员字段是身份账号列表的补充信息，按 sub 关联，不复制到 IAM。
function fetchConsoleMemberPage(params: Page) {
  return request.Get<Service.PageResult<Entity.ConsoleMember>>('/user/list', { params })
}

// ---- 身份账号（IAM 身份 + 控制台成员信息）----
export async function fetchAccountPage(params: Page & { username?: string, tenant_id?: string, status?: string, org_id?: number | null }): Promise<Service.PageResult<Entity.IdentityAccount>> {
  const [accounts, members] = await Promise.all([
    request.Get<Service.PageResult<Entity.Account>>('/account/list', { params }),
    fetchConsoleMemberPage({ page: 1, page_size: 500 }),
  ])
  if (!accounts.isSuccess)
    return { ...accounts, data: [] }
  if (!members.isSuccess) {
    return {
      ...accounts,
      isSuccess: false,
      errorType: members.errorType,
      code: members.code,
      message: members.message,
      data: [],
    }
  }
  return {
    ...accounts,
    data: accounts.data.map((account) => {
      const member = members.data.find(user => user.sub === account.sub)
      return {
        ...account,
        console_member: member
          ? {
              sub: member.sub,
              roles: member.roles,
              is_superuser: member.is_superuser,
              is_active: member.is_active,
              last_login: member.last_login,
            }
          : null,
      }
    }),
  }
}
export const fetchCreateAccount = (data: Partial<Entity.AccountForm>) => request.Post<Ok>('/account/create', data)
export const fetchUpdateAccount = (data: Partial<Entity.AccountForm> & Pick<Entity.Account, 'sub'>) => request.Post<Ok>('/account/update', data)
export const fetchDeleteAccount = (sub: string) => request.Delete<Ok>('/account/delete', undefined, { params: { sub } })
export const fetchUpdateMemberRoles = (data: { sub: string, tenant_id: string, role_ids: number[] }) => request.Post<Ok>('/user/roles', data)

export function fetchTenantPage(params: Page & { name?: string }) {
  return request.Get<Service.PageResult<Entity.Tenant>>('/tenant/list', { params })
}
export const fetchCreateTenant = (data: Pick<Entity.Tenant, 'name'>) => request.Post<Ok>('/tenant/create', data)
export const fetchUpdateTenant = (data: Entity.Tenant) => request.Post<Ok>('/tenant/update', data)
export const fetchDeleteTenant = (tenant_id: string) => request.Delete<Ok>('/tenant/delete', undefined, { params: { tenant_id } })

// ---- 机构 ----
type OrgForm = Pick<Entity.Org, 'parent_id' | 'code' | 'name' | 'sort_order'> & { tenant_id?: string }
export const fetchOrgTree = (tenant_id = '') => request.Get<Service.ResponseResult<Entity.Org[]>>('/org/tree', { params: { tenant_id } })
export const fetchCreateOrg = (data: OrgForm) => request.Post<Ok>('/org/create', data)
export const fetchUpdateOrg = (data: OrgForm & Pick<Entity.Org, 'id' | 'status'>) => request.Post<Ok>('/org/update', data)
export const fetchDeleteOrg = (id: number, tenant_id = '') => request.Delete<Ok>('/org/delete', undefined, { params: { id, tenant_id } })
export const fetchImportOrgs = (data: { tenant_id?: string, orgs: Omit<Entity.Org, 'level'>[] }) => request.Post<Ok>('/org/import', data)

// ---- 应用接入 ----
type AppForm = Pick<Entity.App, 'client_id' | 'name' | 'owner' | 'tenants' | 'scopes' | 'redirect_uris' | 'post_logout_redirect_uris' | 'portal'> & { gateway: Entity.AppGateway | null }
export const fetchAppList = (keyword = '') => request.Get<Service.ResponseResult<Entity.App[]>>('/app/list', { params: { keyword } })
export const fetchCreateApp = (data: AppForm) => request.Post<Service.ResponseResult<{ app: Entity.App, secrets: Entity.AppSecrets }>>('/app/create', data)
export const fetchUpdateApp = (data: AppForm) => request.Post<Service.ResponseResult<{ secrets: Entity.AppSecrets }>>('/app/update', data)
export const fetchAppStatus = (client_id: string, status: Entity.App['status']) => request.Post<Ok>('/app/status', { client_id, status })
export const fetchSyncApp = (client_id: string) => request.Post<Ok>('/app/sync', { client_id })
export const fetchRotateAppSecret = (client_id: string, kind: 'client' | 'gateway') => request.Post<Service.ResponseResult<{ secrets: Entity.AppSecrets }>>('/app/secret/rotate', { client_id, kind })

// ---- 角色 ----
export function fetchRolePage(params: Page & { role_name?: string }) {
  return request.Get<Service.PageResult<Entity.Role>>('/role/list', { params })
}
export const fetchCreateRole = (data: Partial<Entity.Role>) => request.Post<Ok>('/role/create', data)
export const fetchUpdateRole = (data: Partial<Entity.Role>) => request.Post<Ok>('/role/update', data)
export const fetchDeleteRole = (role_id: number) => request.Delete<Ok>('/role/delete', undefined, { params: { role_id } })
export function fetchRoleAuthorized(id: number) {
  return request.Get<Service.ResponseResult<Entity.Role & { menus: Entity.Menu[], apis: Entity.Api[] }>>('/role/authorized', { params: { id } })
}
export function fetchUpdateRoleAuthorized(data: { id: number, menu_ids: number[], api_infos: { path: string, method: string }[] }) {
  return request.Post<Ok>('/role/authorized', data)
}

// ---- 菜单 ----
export const fetchMenuTree = () => request.Get<Service.PageResult<Entity.Menu>>('/menu/list', { params: { page: 1, page_size: 9999 } })
export const fetchCreateMenu = (data: Partial<Entity.Menu>) => request.Post<Ok>('/menu/create', data)
export const fetchUpdateMenu = (data: Partial<Entity.Menu>) => request.Post<Ok>('/menu/update', data)
export const fetchDeleteMenu = (id: number) => request.Delete<Ok>('/menu/delete', undefined, { params: { id } })

// ---- API ----
export function fetchApiPage(params: Page & { path?: string, summary?: string, tags?: string }) {
  return request.Get<Service.PageResult<Entity.Api>>('/api/list', { params })
}
export const fetchCreateApi = (data: Partial<Entity.Api>) => request.Post<Ok>('/api/create', data)
export const fetchUpdateApi = (data: Partial<Entity.Api>) => request.Post<Ok>('/api/update', data)
export const fetchDeleteApi = (api_id: number) => request.Delete<Ok>('/api/delete', undefined, { params: { api_id } })
export const fetchRefreshApi = () => request.Post<Ok>('/api/refresh')

// ---- 审计日志 ----
export function fetchAuditLogPage(params: Page & Record<string, string | number | undefined>) {
  return request.Get<Service.PageResult<Entity.AuditLog>>('/auditlog/list', { params })
}
