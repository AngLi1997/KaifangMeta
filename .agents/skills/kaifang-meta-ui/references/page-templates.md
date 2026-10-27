# 页面模板

以下模板取自现有页面（`views/system/role`、`views/system/menu`），新页面复制后改字段即可。

## 列表页 `views/<目录>/index.vue`

```vue
<script setup lang="tsx">
import type { DataTableColumns } from 'naive-ui'
import { usePageTable, usePermission } from '@/hooks'
import { fetchDeleteRole, fetchRolePage } from '@/service'
import { message } from '@/utils'
import { NButton, NPopconfirm, NTag } from 'naive-ui'
import { COL_WIDTH, colWidth, renderTableActions } from '@/utils/table'
import RoleModal from './components/RoleModal.vue'

const { hasPermission } = usePermission()
const modalRef = ref<InstanceType<typeof RoleModal>>()
const { loading, rows, total, query, fetch, search, reset, changePage } = usePageTable(fetchRolePage, { role_name: '' })

async function remove(id: number) {
  if ((await fetchDeleteRole(id)).isSuccess) {
    message.success('已删除')
    fetch()
  }
}

const columns: DataTableColumns<Entity.Role> = [
  { title: '名称', key: 'name', width: colWidth(0, 10, 16), render: row => <NTag type="info">{row.name}</NTag> },
  { title: '描述', key: 'desc', minWidth: colWidth(0, 16), ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'created_at', width: COL_WIDTH.datetime },
  {
    title: '操作',
    key: 'actions',
    fixed: 'right',
    align: 'center',
    width: COL_WIDTH.actions,
    render: row => renderTableActions([
      hasPermission('post/api/v1/role/update') && (
        <NButton size="small" text onClick={() => modalRef.value?.open(row)}>编辑</NButton>
      ),
      hasPermission('delete/api/v1/role/delete') && (
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
      <n-form-item label="名称">
        <n-input v-model:value="query.role_name" clearable />
      </n-form-item>
    </SearchCard>

    <n-card class="min-h-0 flex-1" content-class="flex min-h-0 flex-col">
      <template #header>
        <n-button v-permission="'post/api/v1/role/create'" type="primary" @click="modalRef?.open()">
          <template #icon>
            <icon-park-outline-add-one />
          </template>
          新建角色
        </n-button>
      </template>
      <DataTable :count="total" :columns="columns" :data="rows" :loading="loading" :row-key="(r: Entity.Role) => r.id" @change="changePage" />
    </n-card>
  </div>

  <RoleModal ref="modalRef" @success="fetch" />
</template>
```

## 新增 / 编辑弹窗 `components/XxxModal.vue`

对外只暴露 `open(row?)`，保存成功 `emit('success')` 由列表刷新。

```vue
<script setup lang="ts">
import type { FormInst } from 'naive-ui'
import { fetchCreateRole, fetchUpdateRole } from '@/service'
import { message } from '@/utils'

const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<Partial<Entity.Role>>({})

function open(row?: Entity.Role) {
  form.value = row ? { id: row.id, name: row.name, desc: row.desc } : { name: '', desc: '' }
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const res = form.value.id ? await fetchUpdateRole(form.value) : await fetchCreateRole(form.value)
  loading.value = false
  if (res.isSuccess) {
    message.success('已保存')
    visible.value = false
    emit('success')
  }
}

defineExpose({ open })
</script>

<template>
  <FormModal
    v-model:show="visible"
    :title="form.id ? '编辑角色' : '新建角色'"
    size="sm"
    :loading="loading"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" label-placement="left" :label-width="70">
      <n-form-item label="名称" path="name" :rule="{ required: true, message: '请输入角色名称', trigger: 'blur' }">
        <n-input v-model:value="form.name" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
```

## 其他形态

| 场景 | 写法 | 参考 |
|------|------|------|
| 左树右表 | `n-flex :wrap="false"`，左 `n-card class="w-60 shrink-0"` 放 `n-tree`，右侧 `n-space vertical class="flex-1 min-w-0"` | `views/system/user` |
| 树形表格 | `DataTable`（不传 `count`）+ `v-model:expanded-row-keys`（异步数据加载后显式展开，`default-expand-all` 只对首屏数据生效） | `views/system/menu`、`dept` |
| 次级配置 | `n-drawer` + `n-drawer-content`（`closable`，footer 放保存）；多类配置用 `n-tabs` | `views/system/role/components/AuthorizeDrawer.vue` |
| 详情查看 | 只读内容用抽屉；JSON 用 `n-code language="json" word-wrap` | `views/system/auditlog` |
| 统计卡片 | `n-grid cols="1 s:2 l:4" responsive="screen"` + `n-card` + `n-thing` + `n-icon-wrapper` + `n-statistic` | `views/dashboard/workbench` |
| 带级联勾选的授权树 | 回填只勾叶子，保存时按树补全上级 | `AuthorizeDrawer.vue` |
