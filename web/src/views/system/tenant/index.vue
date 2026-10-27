<script setup lang="tsx">
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchTenantPage } from '@/service'
import CopyText from '@/components/custom/CopyText.vue'
import { COL_WIDTH, colWidth } from '@/utils/table'
import { NButton, NTag } from 'naive-ui'
import TenantModal from './components/TenantModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof TenantModal>>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchTenantPage, { name: '' })

const columns: DataTableColumns<Entity.Tenant> = [
  { title: '租户名称', key: 'name', minWidth: colWidth(0, 12), ellipsis: { tooltip: true } },
  { title: '租户 ID', key: 'id', width: COL_WIDTH.id, render: row => <CopyText value={row.id} maxLength="none" /> },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: COL_WIDTH.status,
    render: row => <NTag size="small" type={row.status === 'active' ? 'success' : 'error'}>{row.status === 'active' ? '启用' : '停用'}</NTag>,
  },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => hasPermission('post/api/v1/tenant/update')
      ? <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      : '-',
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="租户名称">
        <n-input v-model:value="query.name" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/tenant/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建租户
        </NButton>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.Tenant) => r.id" @change="changePage" />
    </n-card>
  </div>
  <TenantModal ref="modalRef" @success="fetch" />
</template>
