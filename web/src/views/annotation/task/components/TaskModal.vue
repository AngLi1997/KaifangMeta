<script setup lang="ts">
import type { FormInst, FormRules } from 'naive-ui'
import { fetchAnnotationTemplatePage, fetchCreateAnnotationTask } from '@/service'
import { message } from '@/utils'

const emit = defineEmits<{ success: [task: Entity.AnnotationTask] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<{ name: string, template_id: number | null }>({ name: '', template_id: null })
const templates = ref<Entity.AnnotationTemplate[]>([])
const rules: FormRules = {
  name: { required: true, message: '请输入工单名称', trigger: 'blur' },
  template_id: { required: true, type: 'number', message: '请选择场景模板', trigger: 'change' },
}

async function open() {
  form.value = { name: '', template_id: null }
  visible.value = true
  const res = await fetchAnnotationTemplatePage({ page: 1, page_size: 500 })
  if (res.isSuccess)
    templates.value = res.data
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const res = await fetchCreateAnnotationTask({ name: form.value.name, template_id: form.value.template_id! })
  loading.value = false
  if (res.isSuccess) {
    message.success('已创建')
    visible.value = false
    emit('success', res.data)
  }
}

defineExpose({ open })
</script>

<template>
  <FormModal v-model:show="visible" title="新建工单" size="sm" :loading="loading" @submit="submit">
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="80">
      <n-form-item label="名称" path="name">
        <n-input v-model:value="form.name" />
      </n-form-item>
      <n-form-item label="场景模板" path="template_id">
        <n-select
          v-model:value="form.template_id"
          filterable
          :options="templates.map(t => ({ value: t.id, label: `${t.name}（${t.code}@${t.version}）` }))"
        />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
