<script setup lang="tsx">
import { message } from '@/utils'
import type { DataTableColumns } from 'naive-ui'
import { usePermission } from '@/hooks'
import { fetchAppList, fetchAppStatus, fetchRotateAppSecret, fetchSyncApp } from '@/service'
import CopyText from '@/components/custom/CopyText.vue'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import { NButton, NPopconfirm, NTag } from 'naive-ui'
import AppModal from './components/AppModal.vue'
import SecretModal from './components/SecretModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof AppModal>>()
const secretRef = ref<InstanceType<typeof SecretModal>>()
const loading = ref(false)
const rows = ref<Entity.App[]>([])
const keyword = ref('')

async function load() {
  loading.value = true
  rows.value = (await fetchAppList(keyword.value.trim())).data ?? []
  loading.value = false
}
onMounted(load)

async function setStatus(row: Entity.App, status: Entity.App['status']) {
  if ((await fetchAppStatus(row.client_id, status)).isSuccess) {
    message.success(status === 'online' ? '已上线' : '已停用')
    load()
  }
}

async function sync(row: Entity.App) {
  if ((await fetchSyncApp(row.client_id)).isSuccess) {
    message.success('已下发')
    load()
  }
}

async function rotate(row: Entity.App, kind: 'client' | 'gateway') {
  const res = await fetchRotateAppSecret(row.client_id, kind)
  if (res.isSuccess)
    secretRef.value?.open(row.client_id, res.data.secrets)
}

const GATEWAY_STATE = {
  synced: { label: '已下发', type: 'success' },
  pending: { label: '待下发', type: 'warning' },
  drift: { label: '配置漂移', type: 'error' },
} as const

const columns: DataTableColumns<Entity.App> = [
  { title: '应用', key: 'name', minWidth: colWidth(0, 8), ellipsis: { tooltip: true } },
  { title: 'client_id', key: 'client_id', width: colWidth(28, 0, 20), render: row => <CopyText value={row.client_id} maxLength="none" /> },
  { title: '类型', key: 'type', align: 'center', width: 80 },
  {
    title: '开通租户',
    key: 'tenants',
    width: colWidth(0, 10, 16),
    render: row => (
      <span>
        <NTag size="small">{row.tenant_names?.[0] ?? row.tenants[0]}</NTag>
        {row.tenants.length > 1 && <span class="ml-1 text-[var(--text-color-3)]">{`+${row.tenants.length - 1}`}</span>}
      </span>
    ),
  },
  { title: '网关前缀', key: 'gateway.prefix', minWidth: colWidth(20), render: row => row.gateway?.prefix || '-' },
  {
    title: '网关',
    key: 'gateway_state',
    align: 'center',
    width: colWidth(0, 4, 16),
    render: (row) => {
      const state = row.gateway_state && GATEWAY_STATE[row.gateway_state]
      return state ? <NTag size="small" type={state.type}>{state.label}</NTag> : '-'
    },
  },
  {
    title: '实例',
    key: 'instances',
    align: 'center',
    width: 70,
    render: (row) => {
      const i = row.instances
      return i ? <span class={i.healthy < i.total ? 'text-[var(--warning-color)]' : ''}>{`${i.healthy} / ${i.total}`}</span> : '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: COL_WIDTH.status + 14,
    render: row => <NTag size="small" type={row.status === 'online' ? 'success' : 'default'}>{row.status === 'online' ? '已上线' : '已停用'}</NTag>,
  },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      hasPermission('post/api/v1/app/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('post/api/v1/app/status') && (
        <NPopconfirm onPositiveClick={() => setStatus(row, row.status === 'online' ? 'disabled' : 'online')}>
          {{
            default: () => row.status === 'online' ? '停用后网关返回 503，用户无法进入该应用。确认停用？' : '确认上线？',
            trigger: () => <NButton size="small" text type={row.status === 'online' ? 'error' : 'primary'}>{row.status === 'online' ? '停用' : '上线'}</NButton>,
          }}
        </NPopconfirm>
      ),
      hasPermission('post/api/v1/app/sync') && row.gateway_state && row.gateway_state !== 'synced' && (
        <NButton size="small" text onClick={() => sync(row)}>重新下发</NButton>
      ),
      hasPermission('post/api/v1/app/secret/rotate') && (
        <NPopconfirm onPositiveClick={() => rotate(row, 'client')}>
          {{ default: () => '旧 client_secret 立即失效，确认轮换？', trigger: () => <NButton size="small" text>轮换应用密钥</NButton> }}
        </NPopconfirm>
      ),
      hasPermission('post/api/v1/app/secret/rotate') && Boolean(row.gateway?.prefix) && (
        <NPopconfirm onPositiveClick={() => rotate(row, 'gateway')}>
          {{ default: () => '旧网关密钥立即失效，业务后端需同步更新。确认轮换？', trigger: () => <NButton size="small" text>轮换网关密钥</NButton> }}
        </NPopconfirm>
      ),
    ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <SearchCard @search="load" @reset="() => { keyword = ''; load() }">
      <n-form-item label="应用">
        <n-input v-model:value="keyword" clearable placeholder="名称或 client_id" />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <NButton v-permission="'post/api/v1/app/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          注册应用
        </NButton>
      </template>
      <DataTable :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.App) => r.client_id" />
    </n-card>
  </div>
  <AppModal ref="modalRef" @success="load" @secrets="(id, s) => secretRef?.open(id, s)" />
  <SecretModal ref="secretRef" />
</template>
