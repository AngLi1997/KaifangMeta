<script setup lang="ts">
import { computed } from 'vue'

const route = useRoute()
const iframeSrc = computed(() => {
  const href = route.meta.href
  if (!href)
    return undefined

  const url = new URL(href, location.origin)
  const local = ['localhost', '127.0.0.1']
  if (!local.includes(url.hostname) || (location.protocol !== 'https:' && local.includes(location.hostname)))
    return href

  // 运维控制台与前端同主机：主机跟随当前访问地址；HTTP 直连原端口，HTTPS 走 TLS 反代端口
  url.hostname = location.hostname
  if (location.protocol !== 'https:')
    return url.href
  url.protocol = 'https:'
  if (url.port === '9001')
    url.port = import.meta.env.VITE_MINIO_CONSOLE_HTTPS_PORT || '9444'
  else if (url.port === '9180')
    url.port = import.meta.env.VITE_APISIX_DASHBOARD_HTTPS_PORT || '9181'
  else if (url.port === '9010')
    url.port = import.meta.env.VITE_ETCD_WORKBENCH_HTTPS_PORT || '9011'
  return url.href
})
</script>

<template>
  <n-card class="h-full" content-class="p-0!">
    <iframe :src="iframeSrc" class="block h-full w-full border-0" />
  </n-card>
</template>
