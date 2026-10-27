<script setup lang="tsx">
import type { DataTableColumns } from 'naive-ui'
import { usePageTable } from '@/hooks'
import { fetchAnnotationTaskPage } from '@/service'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NProgress, NTag } from 'naive-ui'
import { TASK_STATUS, toOptions } from '../constants'
import TaskModal from './components/TaskModal.vue'

const router = useRouter()
const modalRef = ref<InstanceType<typeof TaskModal>>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchAnnotationTaskPage, { name: '', status: null as string | null })

const open = (id: number) => router.push({ path: '/annotation/task-detail', query: { id } })

const columns: DataTableColumns<Entity.AnnotationTask> = [
  { title: '工单', key: 'name', minWidth: colWidth(0, 16), ellipsis: { tooltip: true } },
  { title: '场景模板', key: 'template_name', minWidth: colWidth(0, 10), ellipsis: { tooltip: true } },
  { title: '模板版本', key: 'template_ref', width: colWidth(22) },
  { title: '条目', key: 'item_count', align: 'right', width: colWidth(8) },
  {
    title: '进度',
    key: 'labeled_count',
    width: colWidth(0, 0, 160),
    render: row => (
      <NProgress
        type="line"
        color="var(--primary-color)"
        percentage={row.item_count ? Math.round(row.labeled_count / row.item_count * 100) : 0}
        indicator-placement="inside"
      />
    ),
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: COL_WIDTH.status,
    render: row => <NTag size="small" type={TASK_STATUS[row.status].type}>{TASK_STATUS[row.status].label}</NTag>,
  },
  { title: '创建人', key: 'creator_name', width: colWidth(0, 6) },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      <NButton size="small" text type="primary" onClick={() => open(row.id)}>打开</NButton>,
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="工单">
        <n-input v-model:value="query.name" clearable />
      </n-form-item>
      <n-form-item label="状态">
        <n-select v-model:value="query.status" :options="toOptions(TASK_STATUS)" clearable class="w-36" />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/annotation/task/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建工单
        </NButton>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.AnnotationTask) => r.id" @change="changePage" />
    </n-card>
  </div>
  <TaskModal ref="modalRef" @success="(task) => { fetch(); open(task.id) }" />
</template>
