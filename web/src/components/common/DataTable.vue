<script setup lang="ts">
import type { DataTableColumns } from 'naive-ui'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ count?: number, columns: DataTableColumns<any> }>()
const emit = defineEmits<{ change: [page: number, pageSize: number] }>()
const attrs = useAttrs()

// 未显式传 scroll-x 时按列宽之和计算：容器不够宽时横向滚动，而不是挤压换行
const scrollX = computed(() => (attrs['scroll-x'] ?? attrs.scrollX ?? props.columns.reduce((sum, column) => {
  const { width, minWidth } = column as { width?: number | string, minWidth?: number | string }
  return sum + (Number(width ?? minWidth) || 120)
}, 0)) as number | string)
</script>

<template>
  <div class="flex h-full min-h-0 flex-1 flex-col">
    <n-data-table v-bind="$attrs" :columns="props.columns" :scroll-x="scrollX" flex-height class="data-table min-h-0 flex-1">
      <template #empty>
        <slot name="empty">
          <n-empty description="暂无数据" />
        </slot>
      </template>
      <template v-if="$slots.loading" #loading>
        <slot name="loading" />
      </template>
    </n-data-table>
    <Pagination
      v-if="props.count !== undefined"
      :count="props.count"
      class="mt-2 shrink-0 self-end"
      @change="(page, pageSize) => emit('change', page, pageSize)"
    />
  </div>
</template>

<style scoped>
/* 单元格不换行：列宽按内容最大长度设定，放不下的长文本列用 ellipsis */
.data-table :deep(.n-data-table-td) {
  white-space: nowrap;
}
</style>
