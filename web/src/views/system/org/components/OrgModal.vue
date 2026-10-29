<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateOrg, fetchUpdateOrg } from '@/service'

const props = defineProps<{ tree: Entity.Org[], tenantId: string }>()
const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
type Form = Pick<Entity.Org, 'parent_id' | 'code' | 'name' | 'sort_order' | 'status'> & { id?: number }
const form = ref<Form>({ parent_id: null, code: '', name: '', sort_order: 0, status: 'active' })
const originalStatus = ref<Entity.Org['status']>('active')
const rules: FormRules = {
  code: { required: true, message: '请输入编码', trigger: 'blur' },
  name: { required: true, message: '请输入名称', trigger: 'blur' },
}

// 编辑时不能选自身及其下级作为上级
const parentOptions = computed(() => {
  const toOption = (o: Entity.Org): any => ({
    key: o.id,
    label: o.name,
    disabled: o.id === form.value.id,
    children: o.id === form.value.id || !o.children?.length ? undefined : o.children.map(toOption),
  })
  return props.tree.map(toOption)
})

function open(row?: Entity.Org, parent?: Entity.Org) {
  form.value = row
    ? { id: row.id, parent_id: row.parent_id, code: row.code, name: row.name, sort_order: row.sort_order, status: row.status }
    : { parent_id: parent?.id ?? null, code: '', name: '', sort_order: 0, status: 'active' }
  originalStatus.value = row?.status ?? 'active'
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const { id, status, ...rest } = form.value
  const data = { ...rest, tenant_id: props.tenantId }
  const res = id ? await fetchUpdateOrg({ ...data, id, status }) : await fetchCreateOrg(data)
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
    :title="form.id ? '编辑机构' : '新增机构'"
    :loading="loading"
    :confirm="form.id && originalStatus === 'active' && form.status === 'disabled' ? '停用后，该机构不再出现在机构选择中。' : undefined"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="70">
      <n-form-item label="上级" path="parent_id">
        <n-tree-select v-model:value="form.parent_id" :options="parentOptions" clearable filterable placeholder="无（根机构）" />
      </n-form-item>
      <n-form-item label="名称" path="name">
        <n-input v-model:value="form.name" :maxlength="128" />
      </n-form-item>
      <n-form-item label="编码" path="code">
        <n-input v-model:value="form.code" :maxlength="64" />
      </n-form-item>
      <n-form-item label="排序" path="sort_order">
        <n-input-number v-model:value="form.sort_order" :min="0" class="w-full" />
      </n-form-item>
      <n-form-item v-if="form.id" label="状态" path="status">
        <n-select v-model:value="form.status" :options="[{ label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
