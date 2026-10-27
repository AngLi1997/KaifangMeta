<script setup lang="ts">
import AnnotationCanvas from '@/components/custom/AnnotationCanvas.vue'
import { fetchAnnotationWorkItem, fetchSaveAnnotationItem } from '@/service'
import { message } from '@/utils'
import { ITEM_STATUS } from '../constants'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.query.task_id)
const work = ref<Entity.AnnotationWorkItem>()
const saving = ref(false)
const canvasRef = ref<InstanceType<typeof AnnotationCanvas>>()

async function load(itemId?: number) {
  const res = await fetchAnnotationWorkItem(taskId, itemId)
  if (!res.isSuccess)
    return
  work.value = res.data
}

async function submit() {
  const result = canvasRef.value?.getResult()
  if (!work.value || !result)
    return
  if (!result.length)
    return message.warning('还没有标注内容')
  saving.value = true
  const res = await fetchSaveAnnotationItem({ id: work.value.item.id, result })
  saving.value = false
  if (!res.isSuccess)
    return
  message.success('已提交')
  if (work.value.next_id)
    load(work.value.next_id)
  else
    load(work.value.item.id)
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
        <n-tag size="small" :type="ITEM_STATUS[work.item.status].type">
          {{ ITEM_STATUS[work.item.status].label }}
        </n-tag>
        <n-text depth="3">
          {{ work.item.name }} · {{ work.index }} / {{ work.task.item_count }}
        </n-text>
      </n-space>
    </template>
    <template #header-extra>
      <n-space>
        <n-button :disabled="!work.prev_id" @click="load(work.prev_id!)">
          上一份
        </n-button>
        <n-button :disabled="!work.next_id" @click="load(work.next_id!)">
          下一份
        </n-button>
        <n-button v-permission="'post/api/v1/annotation/item/save'" type="primary" :loading="saving" @click="submit">
          {{ work.next_id ? '提交并下一份' : '提交' }}
        </n-button>
      </n-space>
    </template>
    <AnnotationCanvas
      ref="canvasRef"
      class="min-h-0 flex-1"
      :config="work.task.config!"
      :data="work.item.data!"
      :result="work.item.result"
    />
  </n-card>
</template>
