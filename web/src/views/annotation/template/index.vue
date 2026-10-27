<script setup lang="tsx">
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchAnnotationTemplatePage } from '@/service'
import { useAuthStore } from '@/store'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NTag } from 'naive-ui'
import { MODALITY, toOptions } from '../constants'

const router = useRouter()
const authStore = useAuthStore()
const { hasPermission } = usePermission()
const { loading, rows, total, query, search, reset, changePage } = usePageTable(fetchAnnotationTemplatePage, { name: '', modality: null as string | null })

const edit = (id?: number) => router.push({ path: '/annotation/template-edit', query: id ? { id } : {} })

const columns: DataTableColumns<Entity.AnnotationTemplate> = [
  { title: '名称', key: 'name', minWidth: colWidth(0, 10), ellipsis: { tooltip: true } },
  { title: '编码', key: 'code', width: colWidth(18) },
  { title: '模态', key: 'modality', width: colWidth(0, 4), render: row => MODALITY[row.modality] },
  {
    title: '范围',
    key: 'scope',
    align: 'center',
    width: COL_WIDTH.status,
    render: row => <NTag size="small" type={row.scope === 'system' ? 'info' : 'default'}>{row.scope === 'system' ? '系统' : '本租户'}</NTag>,
  },
  { title: '版本', key: 'version', align: 'right', width: colWidth(6), render: row => `v${row.version}` },
  { title: '更新时间', key: 'updated_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      <NButton size="small" text type="primary" onClick={() => edit(row.id)}>
        {row.tenant_id === authStore.userInfo?.tenant_id && hasPermission('post/api/v1/annotation/template/update') ? '编辑' : '预览'}
      </NButton>,
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="名称">
        <n-input v-model:value="query.name" clearable />
      </n-form-item>
      <n-form-item label="模态">
        <n-select v-model:value="query.modality" :options="toOptions(MODALITY)" clearable class="w-32" />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/annotation/template/create'" type="primary" @click="edit()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建模板
        </NButton>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.AnnotationTemplate) => r.id" @change="changePage" />
    </n-card>
  </div>
</template>
