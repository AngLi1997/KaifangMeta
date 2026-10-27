<script setup lang="tsx">
import type { DataTableColumns, UploadCustomRequestOptions } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchAnnotationItemPage, fetchAnnotationTask, fetchUploadAnnotationItem } from '@/service'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NTag } from 'naive-ui'
import { ITEM_STATUS, TASK_STATUS, toOptions } from '../constants'

const route = useRoute()
const router = useRouter()
const { hasPermission } = usePermission()
const taskId = Number(route.query.id)
const task = ref<Entity.AnnotationTask>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(
  fetchAnnotationItemPage,
  { task_id: taskId, name: '', status: null as string | null },
)

async function loadTask() {
  const res = await fetchAnnotationTask(taskId)
  if (res.isSuccess)
    task.value = res.data
}

async function upload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  const data = new FormData()
  data.append('task_id', String(taskId))
  data.append('file', file.file!)
  const res = await fetchUploadAnnotationItem(data)
  if (!res.isSuccess)
    return onError()
  onFinish()
  loadTask()
  fetch()
}

function label(itemId?: number) {
  return router.push({ path: '/annotation/workbench', query: itemId ? { task_id: taskId, item_id: itemId } : { task_id: taskId } })
}

const columns: DataTableColumns<Entity.AnnotationItem> = [
  { title: '文件', key: 'name', minWidth: colWidth(0, 20), ellipsis: { tooltip: true } },
  { title: '条目 ID', key: 'item_key', width: colWidth(16) },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: COL_WIDTH.status,
    render: row => <NTag size="small" type={ITEM_STATUS[row.status].type}>{ITEM_STATUS[row.status].label}</NTag>,
  },
  { title: '标注人', key: 'annotator_name', width: colWidth(0, 6), render: row => row.annotator_name || '-' },
  { title: '标注时间', key: 'annotated_at', width: COL_WIDTH.datetime, render: row => row.annotated_at || '-' },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      hasPermission('get/api/v1/annotation/item/get') && (
        <NButton size="small" text type="primary" onClick={() => label(row.id)}>
          {row.status === 'LABELED' ? '查看' : '标注'}
        </NButton>
      ),
    ]),
  },
]

onMounted(loadTask)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <n-card v-if="task" :title="task.name">
      <template #header-extra>
        <n-space>
          <n-upload
            v-permission="'post/api/v1/annotation/task/upload'"
            multiple
            :show-file-list="false"
            accept="image/*,video/*,audio/*,text/plain"
            :custom-request="upload"
          >
            <NButton>
              <template #icon>
                <icon-park-outline-upload-one />
              </template>
              上传数据
            </NButton>
          </n-upload>
          <NButton type="primary" :disabled="!task.item_count" @click="label()">
            <template #icon>
              <icon-park-outline-play />
            </template>
            开始标注
          </NButton>
        </n-space>
      </template>
      <n-descriptions :column="4" label-placement="left">
        <n-descriptions-item label="场景模板">
          {{ task.template_name }}（{{ task.template_ref }}）
        </n-descriptions-item>
        <n-descriptions-item label="状态">
          <NTag size="small" :type="TASK_STATUS[task.status].type">
            {{ TASK_STATUS[task.status].label }}
          </NTag>
        </n-descriptions-item>
        <n-descriptions-item label="进度">
          {{ task.labeled_count }} / {{ task.item_count }}
        </n-descriptions-item>
        <n-descriptions-item label="创建">
          {{ task.creator_name }} · {{ task.created_at }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <SearchCard @search="search" @reset="reset">
      <n-form-item label="文件">
        <n-input v-model:value="query.name" clearable />
      </n-form-item>
      <n-form-item label="状态">
        <n-select v-model:value="query.status" :options="toOptions(ITEM_STATUS)" clearable class="w-36" />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.AnnotationItem) => r.id" @change="changePage" />
    </n-card>
  </div>
</template>
