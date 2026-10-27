<script setup lang="ts">
import { handleCallback, startLogin } from '@/service'

const router = useRouter()
const route = useRoute()
const error = ref('')

onMounted(async () => {
  try {
    const returnTo = await handleCallback(route.query as Record<string, string>)
    if (returnTo)
      router.replace(returnTo)
  }
  catch (e) {
    error.value = (e as Error).message
  }
})

function retry() {
  startLogin({ silent: false, returnTo: '/' })
}
</script>

<template>
  <div class="wh-full flex-center">
    <n-result v-if="error" status="error" :title="error">
      <template #footer>
        <n-button type="primary" @click="retry">
          重新登录
        </n-button>
      </template>
    </n-result>
    <n-spin v-else size="large" />
  </div>
</template>
