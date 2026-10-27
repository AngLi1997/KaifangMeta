<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateTenant, fetchUpdateTenant } from '@/service'

const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<Partial<Entity.Tenant>>({ name: '', status: 'active' })
const originalStatus = ref<Entity.Tenant['status']>('active')
const rules: FormRules = { name: { required: true, message: '请输入租户名称', trigger: 'blur' } }

function open(row?: Entity.Tenant) {
  form.value = row ? { ...row } : { name: '', status: 'active' }
  originalStatus.value = row?.status ?? 'active'
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const res = form.value.id
    ? await fetchUpdateTenant(form.value as Entity.Tenant)
    : await fetchCreateTenant({ name: form.value.name! })
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
    :title="form.id ? '编辑租户' : '新建租户'"
    size="sm"
    :loading="loading"
    :confirm="form.id && originalStatus === 'active' && form.status === 'disabled' ? '停用后，该租户下的账号和应用会暂时无法访问。' : undefined"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="70">
      <n-form-item v-if="form.id" label="ID">
        <n-input :value="form.id" readonly />
      </n-form-item>
      <n-form-item label="名称" path="name">
        <n-input v-model:value="form.name" maxlength="64" />
      </n-form-item>
      <n-form-item v-if="form.id" label="状态" path="status">
        <n-select v-model:value="form.status" :options="[{ label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
