<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst } from 'naive-ui'
import { fetchCreateRole, fetchUpdateRole } from '@/service'

const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<Partial<Entity.Role>>({})

function open(row?: Entity.Role) {
  form.value = row ? { id: row.id, name: row.name, desc: row.desc, scope: row.scope } : { name: '', desc: '', scope: 'tenant' }
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
      <n-form-item label="范围" path="scope">
        <n-radio-group v-model:value="form.scope">
          <n-radio value="tenant">
            租户
          </n-radio>
          <n-radio value="system">
            系统
          </n-radio>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="描述" path="desc">
        <n-input v-model:value="form.desc" type="textarea" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
