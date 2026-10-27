<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchDeleteRole, fetchRolePage } from '@/service'
import { NButton, NPopconfirm, NTag } from 'naive-ui'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import AuthorizeDrawer from './components/AuthorizeDrawer.vue'
import RoleModal from './components/RoleModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof RoleModal>>()
const drawerRef = ref<InstanceType<typeof AuthorizeDrawer>>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchRolePage, { role_name: '' })

async function remove(id: number) {
  if ((await fetchDeleteRole(id)).isSuccess) {
    message.success('已删除')
    fetch()
  }
}

const columns: DataTableColumns<Entity.Role> = [
  { title: '名称', key: 'name', width: colWidth(0, 10, 16), render: row => <NTag type="info">{row.name}</NTag> },
  { title: '范围', key: 'scope', width: COL_WIDTH.status, render: row => <NTag size="small" type={row.scope === 'system' ? 'warning' : 'default'}>{row.scope === 'system' ? '系统' : '租户'}</NTag> },
  { title: '描述', key: 'desc', minWidth: colWidth(0, 16), ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: colWidth(0, 8, 32),
    render: row => renderTableActions([
      hasPermission('post/api/v1/role/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('get/api/v1/role/authorized') && (
        <NButton size="small" type="primary" text onClick={() => drawerRef.value?.open(row)}>设置权限</NButton>
      ),
      hasPermission('delete/api/v1/role/delete') && (
        <NPopconfirm onPositiveClick={() => remove(row.id)}>
          {{ default: () => '确认删除该角色？', trigger: () => <NButton size="small" type="error" text>删除</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="名称">
        <n-input v-model:value="query.role_name" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/role/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建角色
        </NButton>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.Role) => r.id" @change="changePage" />
    </n-card>
  </div>

  <RoleModal ref="modalRef" @success="fetch" />
  <AuthorizeDrawer ref="drawerRef" />
</template>
