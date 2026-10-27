<script setup lang="ts">
import Workbench from '@/components/custom/workbench/Workbench.vue'
import { fetchAnnotationWorkItem, fetchSaveAnnotationItem } from '@/service'
import { message } from '@/utils'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.query.task_id)
const work = ref<Entity.AnnotationWorkItem>()
const saving = ref(false)

async function load(itemId?: number) {
  const res = await fetchAnnotationWorkItem(taskId, itemId)
  if (!res.isSuccess)
    return
  work.value = res.data
}

async function save(result: Record<string, unknown>[], draft: boolean) {
  if (!work.value)
    return
  if (!draft && !result.length)
    return message.warning('还没有标注内容')
  saving.value = true
  const res = await fetchSaveAnnotationItem({ id: work.value.item.id, result, draft })
  saving.value = false
  if (!res.isSuccess)
    return
  message.success(draft ? '已保存' : '已提交')
  if (!draft)
    load(work.value.next_id ?? work.value.item.id)
}

onMounted(() => load(Number(route.query.item_id) || undefined))
</script>

<template>
  <n-card v-if="work" class="h-full" content-class="flex min-h-0 flex-col p-0!" :segmented="{ content: true }">
    <template #header>
      <n-space align="center">
        <n-button text @click="router.push({ path: '/annotation/task-detail', query: { id: taskId } })">
          <template #icon>
            <icon-park-outline-left />
          </template>
        </n-button>
        <span>{{ work.task.name }}</span>
      </n-space>
    </template>
    <Workbench
      :config="work.task.config!"
      :data="work.item.data!"
      :result="work.item.result"
      :item="{
        id: work.item.id,
        name: work.item.name,
        index: work.index,
        total: work.task.item_count,
      }"
      :has-prev="!!work.prev_id"
      :has-next="!!work.next_id"
      :loading="saving"
      @save="result => save(result, true)"
      @submit="result => save(result, false)"
      @prev="load(work.prev_id!)"
      @next="load(work.next_id!)"
    />
  </n-card>
</template>
