<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateApi, fetchUpdateApi } from '@/service'

const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<Partial<Entity.Api>>({})
const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map(v => ({ label: v, value: v }))
const rules: FormRules = {
  path: { required: true, message: '请输入路径', trigger: 'blur' },
  method: { required: true, message: '请选择方法', trigger: 'change' },
  tags: { required: true, message: '请输入模块', trigger: 'blur' },
}

function open(row?: Entity.Api) {
  form.value = row ? { ...row } : { path: '', method: 'GET', summary: '', tags: '' }
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const res = form.value.id ? await fetchUpdateApi(form.value) : await fetchCreateApi(form.value)
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
    :title="form.id ? '编辑接口' : '新建接口'"
    :loading="loading"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="70">
      <n-form-item label="路径" path="path">
        <n-input v-model:value="form.path" />
      </n-form-item>
      <n-form-item label="方法" path="method">
        <n-select v-model:value="form.method" :options="methods" />
      </n-form-item>
      <n-form-item label="简介" path="summary">
        <n-input v-model:value="form.summary" />
      </n-form-item>
      <n-form-item label="模块" path="tags">
        <n-input v-model:value="form.tags" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
