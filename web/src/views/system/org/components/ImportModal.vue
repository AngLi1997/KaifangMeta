<script setup lang="ts">
import { message } from '@/utils'
import { fetchImportOrgs } from '@/service'

const props = defineProps<{ tenantId: string }>()
const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const loading = ref(false)
const text = ref('')
const error = ref('')
const example = '[{"id": 100, "parent_id": null, "code": "37", "name": "山东省", "sort_order": 0, "status": "active"}]'

function open() {
  text.value = ''
  error.value = ''
  visible.value = true
}

async function readFile({ file }: { file: { file?: File | null } }) {
  text.value = await file.file?.text() ?? ''
  return false
}

async function submit() {
  let orgs: Omit<Entity.Org, 'level'>[]
  try {
    orgs = JSON.parse(text.value)
    if (!Array.isArray(orgs) || !orgs.length)
      throw new Error('empty')
  }
  catch {
    error.value = '请提供非空的 JSON 数组'
    return
  }
  error.value = ''
  loading.value = true
  const res = await fetchImportOrgs({ tenant_id: props.tenantId, orgs })
  loading.value = false
  if (res.isSuccess) {
    message.success(res.message || '已导入')
    visible.value = false
    emit('success')
  }
}

defineExpose({ open })
</script>

<template>
  <FormModal v-model:show="visible" title="导入机构" size="lg" :loading="loading" @submit="submit">
    <n-space vertical>
      <n-upload accept=".json,application/json" :show-file-list="false" :custom-request="() => {}" @before-upload="readFile">
        <n-button>
          <template #icon>
            <icon-park-outline-upload-one />
          </template>
          选择 JSON 文件
        </n-button>
      </n-upload>
      <n-input v-model:value="text" type="textarea" :rows="12" :placeholder="example" :status="error ? 'error' : undefined" />
      <n-text v-if="error" type="error">
        {{ error }}
      </n-text>
    </n-space>
  </FormModal>
</template>
