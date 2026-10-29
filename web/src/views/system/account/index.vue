<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchAccountPage, fetchDeleteAccount, fetchOrgTree, fetchTenantPage } from '@/service'
import { useAuthStore } from '@/store'
import CopyText from '@/components/custom/CopyText.vue'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NPopconfirm, NSpace, NTag } from 'naive-ui'
import AccountModal from './components/AccountModal.vue'
import MemberRolesModal from './components/MemberRolesModal.vue'

const { hasPermission } = usePermission()
const authStore = useAuthStore()
const modalRef = ref<InstanceType<typeof AccountModal>>()
const rolesRef = ref<InstanceType<typeof MemberRolesModal>>()
const tenants = ref<Entity.Tenant[]>([])
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchAccountPage, {
  username: '',
  tenant_id: '',
  status: '',
  org_id: null as number | null,
})
const orgs = ref<Entity.Org[]>([])
const toOrgOption = (o: Entity.Org): any => ({ key: o.id, label: o.name, children: o.children?.length ? o.children.map(toOrgOption) : undefined })
const orgOptions = computed(() => orgs.value.map(toOrgOption))
// 机构按租户维护：系统租户按所选租户筛选机构
watch(() => query.value.tenant_id, async (tenantId) => {
  query.value.org_id = null
  orgs.value = !authStore.isSystemTenant || tenantId ? (await fetchOrgTree(tenantId)).data ?? [] : []
}, { immediate: true })
const tenantOptions = computed(() => tenants.value.map(tenant => ({ label: tenant.name, value: tenant.id })))
const tenantName = (id: string) => tenants.value.find(tenant => tenant.id === id)?.name ?? id
// 业务租户的管理员只能编辑主租户在本租户的账号
const editable = (row: Entity.IdentityAccount) => authStore.isSystemTenant || row.tenant_id === authStore.userInfo?.tenant_id
const statusOptions = [{ label: '全部', value: '' }, { label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]
onMounted(async () => {
  tenants.value = (await fetchTenantPage({ page: 1, page_size: 500 })).data ?? []
})

async function remove(sub: string) {
  if ((await fetchDeleteAccount(sub)).isSuccess) {
    message.success('已删除')
    fetch()
  }
}

const columns: DataTableColumns<Entity.IdentityAccount> = [
  { title: '登录名', key: 'username', minWidth: colWidth(16), ellipsis: { tooltip: true } },
  { title: '姓名', key: 'name', minWidth: colWidth(0, 6), ellipsis: { tooltip: true }, render: row => row.name || '-' },
  { title: '机构', key: 'org_name', minWidth: colWidth(0, 8), ellipsis: { tooltip: true }, render: row => row.org_name || '-' },
  { title: '电话', key: 'phone', minWidth: colWidth(11), render: row => row.phone || '-' },
  { title: 'sub', key: 'sub', width: COL_WIDTH.id, render: row => <CopyText value={row.sub} maxLength="none" /> },
  {
    title: '租户',
    key: 'tenant_id',
    minWidth: colWidth(0, 12, 24),
    render: row => (
      <NSpace size="small" wrap={false}>
        <NTag size="small">{row.tenant_name ?? row.tenant_id}</NTag>
        {row.member_tenants?.map(tenant => <NTag size="small" bordered={false}>{tenant.name}</NTag>)}
      </NSpace>
    ),
  },
  { title: '邮箱', key: 'email', minWidth: colWidth(24), ellipsis: { tooltip: true } },
  {
    title: '账号状态',
    key: 'status',
    align: 'center',
    width: colWidth(0, 4),
    render: row => <NTag size="small" type={row.status === 'active' ? 'success' : 'error'}>{row.status === 'active' ? '启用' : '停用'}</NTag>,
  },
  {
    title: '控制台角色',
    key: 'console_member.roles',
    minWidth: colWidth(0, 12, 24),
    render: row => row.console_member?.roles?.length
      ? (
          <NSpace size="small" wrap={false}>
            {row.console_member.roles.map(role => (
              <NTag size="small" type="info">
                {authStore.isSystemTenant ? `${tenantName(role.tenant_id)} / ${role.name}` : role.name}
              </NTag>
            ))}
            {row.console_member.is_superuser ? <NTag size="small" type="warning">超级管理员</NTag> : null}
          </NSpace>
        )
      : row.console_member ? '-' : '未开通',
  },
  {
    title: '控制台状态',
    key: 'console_member.is_active',
    align: 'center',
    width: colWidth(0, 5),
    render: row => row.console_member
      ? <NTag size="small" type={row.console_member.is_active ? 'success' : 'error'}>{row.console_member.is_active ? '启用' : '停用'}</NTag>
      : '未开通',
  },
  { title: '最近访问', key: 'console_member.last_login', width: COL_WIDTH.datetime, render: row => row.console_member?.last_login || '-' },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      hasPermission('post/api/v1/account/update') && editable(row) && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('post/api/v1/user/roles') && row.status === 'active' && (
        <NButton size="small" type="primary" text onClick={() => rolesRef.value?.open(row)}>角色</NButton>
      ),
      hasPermission('delete/api/v1/account/delete') && editable(row) && row.status === 'disabled' && !row.console_member?.is_superuser && (
        <NPopconfirm onPositiveClick={() => remove(row.sub)}>
          {{ default: () => '确认删除该账号？', trigger: () => <NButton size="small" type="error" text>删除</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="登录名">
        <n-input v-model:value="query.username" clearable />
      </n-form-item>
      <n-form-item label="租户">
        <n-select v-model:value="query.tenant_id" clearable :options="tenantOptions" class="w-52" />
      </n-form-item>
      <n-form-item v-if="orgs.length" label="机构">
        <n-tree-select v-model:value="query.org_id" :options="orgOptions" clearable filterable class="w-52" />
      </n-form-item>
      <n-form-item label="状态">
        <n-select v-model:value="query.status" :options="statusOptions" class="w-32" />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/account/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建账号
        </NButton>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.IdentityAccount) => r.sub" @change="changePage" />
    </n-card>
  </div>
  <AccountModal ref="modalRef" @success="fetch" />
  <MemberRolesModal ref="rolesRef" @success="fetch" />
</template>
