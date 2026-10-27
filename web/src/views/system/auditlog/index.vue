<script setup lang="tsx">
import type { DataTableColumns } from 'naive-ui'
import { usePageTable } from '@/hooks'
import { fetchAuditLogPage } from '@/service'
import { COL_WIDTH, colWidth } from '@/utils/table'
import { NButton, NTag } from 'naive-ui'

const { loading, rows, total, query, search, reset, changePage } = usePageTable(
  // 时间范围拆成 start_time / end_time 传给后端
  ({ range, ...params }: Record<string, any>) => fetchAuditLogPage({
    ...params,
    start_time: range?.[0] ? new Date(range[0]).toISOString() : undefined,
    end_time: range?.[1] ? new Date(range[1]).toISOString() : undefined,
  }),
  { username: '', module: '', summary: '', path: '', method: null as string | null, range: null as [number, number] | null },
)

const methods = ['GET', 'POST', 'PUT', 'DELETE'].map(v => ({ label: v, value: v }))
const detail = ref<Entity.AuditLog | null>(null)
const pretty = (v: unknown) => JSON.stringify(v, null, 2)

const columns: DataTableColumns<Entity.AuditLog> = [
  { title: '用户', key: 'username', width: colWidth(16), ellipsis: { tooltip: true } },
  { title: '模块', key: 'module', width: colWidth(0, 8), ellipsis: { tooltip: true } },
  { title: '描述', key: 'summary', width: colWidth(0, 12), ellipsis: { tooltip: true } },
  { title: '方法', key: 'method', align: 'center', width: 80 },
  { title: '路径', key: 'path', minWidth: colWidth(40), ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: 80,
    render: row => <NTag size="small" type={row.status < 400 ? 'success' : 'error'}>{row.status}</NTag>,
  },
  { title: '耗时(ms)', key: 'response_time', align: 'center', width: colWidth(4, 2) },
  { title: '时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: 80,
    render: row => <NButton size="small" text onClick={() => (detail.value = row)}>详情</NButton>,
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="用户">
        <n-input v-model:value="query.username" clearable class="w-36" />
      </n-form-item>
      <n-form-item label="模块">
        <n-input v-model:value="query.module" clearable class="w-36" />
      </n-form-item>
      <n-form-item label="路径">
        <n-input v-model:value="query.path" clearable class="w-48" />
      </n-form-item>
      <n-form-item label="方法">
        <n-select v-model:value="query.method" :options="methods" clearable class="w-28" />
      </n-form-item>
      <n-form-item label="时间">
        <n-date-picker v-model:value="query.range" type="datetimerange" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.AuditLog) => r.id" @change="changePage" />
    </n-card>
  </div>

  <n-drawer :show="!!detail" :width="640" @update:show="(v: boolean) => !v && (detail = null)">
    <n-drawer-content :title="`${detail?.method} ${detail?.path}`" closable>
      <n-space vertical>
        <n-h6 prefix="bar">
          请求参数
        </n-h6>
        <n-code :code="pretty(detail?.request_args)" language="json" word-wrap />
        <n-h6 prefix="bar">
          响应内容
        </n-h6>
        <n-code :code="pretty(detail?.response_body)" language="json" word-wrap />
      </n-space>
    </n-drawer-content>
  </n-drawer>
</template>
