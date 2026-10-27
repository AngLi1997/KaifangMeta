<script setup lang="ts">
import { computed } from 'vue'

const route = useRoute()
const iframeSrc = computed(() => {
  const href = route.meta.href
  if (!href)
    return undefined

  const url = new URL(href, location.origin)
  if (location.protocol !== 'https:' && ['localhost', '127.0.0.1'].includes(location.hostname))
    return href
  if (!['localhost', '127.0.0.1'].includes(url.hostname))
    return href

  url.protocol = 'https:'
  url.hostname = location.hostname
  if (url.port === '9001')
    url.port = import.meta.env.VITE_MINIO_CONSOLE_HTTPS_PORT || '9444'
  else if (url.port === '9180')
    url.port = import.meta.env.VITE_APISIX_DASHBOARD_HTTPS_PORT || '9181'
  return url.href
})
</script>

<template>
  <n-card class="h-full" content-class="p-0!">
    <iframe :src="iframeSrc" class="block h-full w-full border-0" />
  </n-card>
</template>
