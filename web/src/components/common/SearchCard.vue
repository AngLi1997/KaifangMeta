<script setup lang="ts">
/** 列表页查询区：nova-admin 风格的行内表单 + 右侧「搜索 / 重置」 */
const emit = defineEmits<{ search: [], reset: [] }>()
</script>

<template>
  <n-card>
    <n-form label-placement="left" inline :show-feedback="false" @keyup.enter="emit('search')">
      <n-flex class="w-full">
        <slot />
        <n-flex class="ml-auto">
          <n-button type="primary" @click="emit('search')">
            <template #icon>
              <icon-park-outline-search />
            </template>
            搜索
          </n-button>
          <n-button strong secondary @click="emit('reset')">
            <template #icon>
              <icon-park-outline-redo />
            </template>
            重置
          </n-button>
        </n-flex>
      </n-flex>
    </n-form>
  </n-card>
</template>
