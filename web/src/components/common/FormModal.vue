<script setup lang="ts">
// 表单弹窗：统一 n-modal 外观与「取消 / 保存」底栏；confirm 非空时保存前二次确认；readonly 时只读查看，底栏只有「关闭」
const props = withDefaults(defineProps<{
  title: string
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  confirm?: string
  readonly?: boolean
}>(), { size: 'md' })

const emit = defineEmits<{ submit: [] }>()
const show = defineModel<boolean>('show', { required: true })
const widthClass = computed(() => ({ sm: 'w-480px', md: 'w-560px', lg: 'w-640px' })[props.size])
</script>

<template>
  <n-modal
    v-model:show="show"
    preset="card"
    :title="title"
    :class="widthClass"
    :mask-closable="false"
    :segmented="{ content: true, action: true }"
  >
    <slot />
    <template #action>
      <n-space v-if="readonly" justify="end">
        <n-button @click="show = false">
          关闭
        </n-button>
      </n-space>
      <n-space v-else justify="end">
        <n-button @click="show = false">
          取消
        </n-button>
        <n-popconfirm v-if="confirm" @positive-click="emit('submit')">
          <template #trigger>
            <n-button type="primary" :loading="loading">
              保存
            </n-button>
          </template>
          {{ confirm }}
        </n-popconfirm>
        <n-button v-else type="primary" :loading="loading" @click="emit('submit')">
          保存
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>
