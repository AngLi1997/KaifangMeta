<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePermission } from '@/hooks'
import { fetchDeleteMenu, fetchMenuTree } from '@/service'
import NovaIcon from '@/components/common/NovaIcon.vue'
import { NButton, NPopconfirm, NTag } from 'naive-ui'
import { colWidth, renderTableActions } from '@/utils/table'
import MenuModal from './components/MenuModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof MenuModal>>()
const loading = ref(false)
const tree = ref<Entity.Menu[]>([])
// 异步加载的树：default-expand-all 只对首屏数据生效，加载后显式展开全部
const expandedKeys = ref<number[]>([])
const collectIds = (items: Entity.Menu[]): number[] => items.flatMap(i => [i.id, ...collectIds(i.children ?? [])])

async function load() {
  loading.value = true
  tree.value = (await fetchMenuTree()).data ?? []
  expandedKeys.value = collectIds(tree.value)
  loading.value = false
}
onMounted(load)

async function remove(id: number) {
  if ((await fetchDeleteMenu(id)).isSuccess) {
    message.success('已删除')
    load()
  }
}

const columns: DataTableColumns<Entity.Menu> = [
  { title: '名称', key: 'name', width: colWidth(0, 10, 48) },
  { title: '图标', key: 'icon', align: 'center', width: 70, render: row => <NovaIcon icon={row.icon ?? undefined} /> },
  {
    title: '类型',
    key: 'menu_type',
    align: 'center',
    width: 80,
    render: row => <NTag size="small" type={row.menu_type === 'catalog' ? 'primary' : 'info'}>{row.menu_type === 'catalog' ? '目录' : '菜单'}</NTag>,
  },
  { title: '路由路径', key: 'path', minWidth: colWidth(24), ellipsis: { tooltip: true } },
  { title: '组件', key: 'component', minWidth: colWidth(24), ellipsis: { tooltip: true } },
  { title: '排序', key: 'order', align: 'center', width: 70 },
  { title: '隐藏', key: 'is_hidden', align: 'center', width: 70, render: row => row.is_hidden ? '是' : '-' },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: colWidth(0, 8, 32),
    render: row => renderTableActions([
      row.menu_type === 'catalog' && hasPermission('post/api/v1/menu/create') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(undefined, row)}>新增下级</NButton>
      ),
      hasPermission('post/api/v1/menu/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('delete/api/v1/menu/delete') && (
        <NPopconfirm onPositiveClick={() => remove(row.id)}>
          {{ default: () => '确认删除？有下级的菜单不能删除', trigger: () => <NButton size="small" type="error" text>删除</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <n-card class="h-full min-h-0" content-class="flex min-h-0 flex-col">
    <template #header>
      <NButton v-permission="'post/api/v1/menu/create'" type="primary" @click="modalRef?.open()">
        <template #icon>
          <icon-park-outline-add-one />
        </template>
        新建菜单
      </NButton>
    </template>
    <DataTable
      v-model:expanded-row-keys="expandedKeys"
      :columns="columns"
      :data="tree"
      :loading="loading"
      :row-key="(r: Entity.Menu) => r.id"
    />
    <MenuModal ref="modalRef" :tree="tree" @success="load" />
  </n-card>
</template>
