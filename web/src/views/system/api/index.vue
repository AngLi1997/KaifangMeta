<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchApiPage, fetchDeleteApi, fetchRefreshApi } from '@/service'
import { NButton, NPopconfirm, NSpace, NTag } from 'naive-ui'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import ApiModal from './components/ApiModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof ApiModal>>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchApiPage, {
  path: '',
  summary: '',
  tags: '',
})

const methodType = { GET: 'success', POST: 'info', PUT: 'warning', PATCH: 'warning', DELETE: 'error' } as const

const refreshing = ref(false)
async function refresh() {
  refreshing.value = true
  const res = await fetchRefreshApi()
  refreshing.value = false
  if (res.isSuccess) {
    message.success('已按代码中的路由同步')
    search()
  }
}

async function remove(id: number) {
  if ((await fetchDeleteApi(id)).isSuccess) {
    message.success('已删除')
    fetch()
  }
}

const columns: DataTableColumns<Entity.Api> = [
  { title: '路径', key: 'path', minWidth: colWidth(40), ellipsis: { tooltip: true } },
  {
    title: '方法',
    key: 'method',
    align: 'center',
    width: 90,
    render: row => <NTag size="small" type={methodType[row.method]}>{row.method}</NTag>,
  },
  { title: '简介', key: 'summary', width: colWidth(0, 12), ellipsis: { tooltip: true } },
  { title: '模块', key: 'tags', width: colWidth(0, 8), ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      hasPermission('post/api/v1/api/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('delete/api/v1/api/delete') && (
        <NPopconfirm onPositiveClick={() => remove(row.id)}>
          {{ default: () => '确认删除？', trigger: () => <NButton size="small" type="error" text>删除</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="search" @reset="reset">
      <n-form-item label="路径">
        <n-input v-model:value="query.path" clearable />
      </n-form-item>
      <n-form-item label="简介">
        <n-input v-model:value="query.summary" clearable />
      </n-form-item>
      <n-form-item label="模块">
        <n-input v-model:value="query.tags" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NSpace>
          <NButton v-permission="'post/api/v1/api/create'" type="primary" @click="modalRef?.open()">
            <template #icon>
              <icon-park-outline-add-one />
            </template>
            新建接口
          </NButton>
          <NButton v-permission="'post/api/v1/api/refresh'" :loading="refreshing" @click="refresh">
            <template #icon>
              <icon-park-outline-refresh />
            </template>
            同步接口
          </NButton>
        </NSpace>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.Api) => r.id" @change="changePage" />
    </n-card>
  </div>

  <ApiModal ref="modalRef" @success="fetch" />
</template>
