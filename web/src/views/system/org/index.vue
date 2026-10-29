<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePermission } from '@/hooks'
import { fetchDeleteOrg, fetchOrgTree, fetchTenantPage } from '@/service'
import { useAuthStore } from '@/store'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NPopconfirm, NTag } from 'naive-ui'
import ImportModal from './components/ImportModal.vue'
import OrgModal from './components/OrgModal.vue'

const { hasPermission } = usePermission()
const authStore = useAuthStore()
const modalRef = ref<InstanceType<typeof OrgModal>>()
const importRef = ref<InstanceType<typeof ImportModal>>()
const loading = ref(false)
const tree = ref<Entity.Org[]>([])
const keyword = ref('')
const tenantId = ref('')
const tenants = ref<Entity.Tenant[]>([])
const tenantOptions = computed(() => tenants.value.map(tenant => ({ label: tenant.name, value: tenant.id })))
const expandedKeys = ref<number[]>([])

// 搜索保留命中节点及其祖先
function filterTree(items: Entity.Org[], word: string): Entity.Org[] {
  return items.flatMap((item) => {
    const children = filterTree(item.children ?? [], word)
    const hit = item.name.includes(word) || item.code.includes(word)
    return hit || children.length ? [{ ...item, children: hit ? item.children : children }] : []
  })
}
function collectIds(items: Entity.Org[], depth = Infinity): number[] {
  return depth <= 0 ? [] : items.flatMap(i => [i.id, ...collectIds(i.children ?? [], depth - 1)])
}
const data = computed(() => keyword.value.trim() ? filterTree(tree.value, keyword.value.trim()) : tree.value)
watch(keyword, () => (expandedKeys.value = collectIds(data.value, keyword.value.trim() ? Infinity : 2)))

async function load() {
  loading.value = true
  tree.value = (await fetchOrgTree(tenantId.value)).data ?? []
  expandedKeys.value = collectIds(tree.value, 2)
  loading.value = false
}
onMounted(async () => {
  if (authStore.isSystemTenant)
    tenants.value = (await fetchTenantPage({ page: 1, page_size: 500 })).data ?? []
  load()
})

async function remove(id: number) {
  if ((await fetchDeleteOrg(id, tenantId.value)).isSuccess) {
    message.success('已删除')
    load()
  }
}

const columns: DataTableColumns<Entity.Org> = [
  { title: '名称', key: 'name', minWidth: colWidth(0, 16, 64), ellipsis: { tooltip: true } },
  { title: '编码', key: 'code', minWidth: colWidth(16) },
  { title: '排序', key: 'sort_order', align: 'center', width: 70 },
  { title: '账号数', key: 'account_count', align: 'center', width: 80 },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: COL_WIDTH.status,
    render: row => <NTag size="small" type={row.status === 'active' ? 'success' : 'error'}>{row.status === 'active' ? '启用' : '停用'}</NTag>,
  },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: colWidth(0, 8, 32),
    render: row => renderTableActions([
      hasPermission('post/api/v1/org/create') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(undefined, row)}>新增下级</NButton>
      ),
      hasPermission('post/api/v1/org/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('delete/api/v1/org/delete') && row.status === 'disabled' && (
        <NPopconfirm onPositiveClick={() => remove(row.id)}>
          {{ default: () => '确认删除该机构？', trigger: () => <NButton size="small" type="error" text>删除</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="load" @reset="() => { keyword = ''; load() }">
      <n-form-item v-if="authStore.isSystemTenant" label="租户">
        <n-select v-model:value="tenantId" :options="tenantOptions" clearable class="w-52" @update:value="load" />
      </n-form-item>
      <n-form-item label="名称 / 编码">
        <n-input v-model:value="keyword" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <n-space>
          <NButton v-permission="'post/api/v1/org/create'" type="primary" @click="modalRef?.open()">
            <template #icon>
              <icon-park-outline-add-one />
            </template>
            新增机构
          </NButton>
          <NButton v-permission="'post/api/v1/org/import'" @click="importRef?.open()">
            <template #icon>
              <icon-park-outline-upload-one />
            </template>
            导入
          </NButton>
        </n-space>
      </template>
      <DataTable
        v-model:expanded-row-keys="expandedKeys"
        :columns="columns"
        :data="data"
        :loading="loading"
        :row-key="(r: Entity.Org) => r.id"
      />
    </n-card>
  </div>
  <OrgModal ref="modalRef" :tree="tree" :tenant-id="tenantId" @success="load" />
  <ImportModal ref="importRef" :tenant-id="tenantId" @success="load" />
</template>
