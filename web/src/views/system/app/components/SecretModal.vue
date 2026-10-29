<script setup lang="ts">
import CopyText from '@/components/custom/CopyText.vue'

const visible = ref(false)
const clientId = ref('')
const secrets = ref<Entity.AppSecrets>({})

function open(id: string, value: Entity.AppSecrets) {
  clientId.value = id
  secrets.value = value
  visible.value = true
}

defineExpose({ open })
</script>

<template>
  <FormModal v-model:show="visible" title="密钥仅显示一次" readonly>
    <n-alert type="warning" :bordered="false" class="mb-4">
      关闭后无法再次查看，请立即保存到业务系统配置。
    </n-alert>
    <n-descriptions :column="1" label-placement="left" bordered :label-style="{ whiteSpace: 'nowrap' }">
      <n-descriptions-item label="client_id">
        <CopyText :value="clientId" max-length="none" />
      </n-descriptions-item>
      <n-descriptions-item v-if="secrets.client_secret" label="client_secret">
        <CopyText :value="secrets.client_secret" max-length="26em" />
      </n-descriptions-item>
      <n-descriptions-item v-if="secrets.gateway_secret" label="gateway_secret">
        <CopyText :value="secrets.gateway_secret" max-length="26em" />
      </n-descriptions-item>
    </n-descriptions>
  </FormModal>
</template>
