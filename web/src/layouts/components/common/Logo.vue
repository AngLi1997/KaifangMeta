<script setup lang="ts">
import { useAppStore } from '@/store'

const router = useRouter()
const appStore = useAppStore()

const name = import.meta.env.VITE_APP_NAME
const logo = '/kaifangdata-logo.png'

const hidenLogoText = computed(() => {
  if (['sidebar', 'mixed-sidebar', 'horizontal'].includes(appStore.layoutMode)) {
    return false
  }
  if (['two-column', 'mixed-two-column'].includes(appStore.layoutMode)) {
    return true
  }
  return appStore.collapsed
})
</script>

<template>
  <div
    class="h-60px text-xl flex-center cursor-pointer gap-2 p-x-2"
    @click="router.push('/')"
  >
    <img :src="logo" alt="" class="h-7 w-7 shrink-0 object-contain">
    <span
      v-show="!hidenLogoText"
      class="text-ellipsis overflow-hidden whitespace-nowrap"
    >{{ name }}</span>
  </div>
</template>

<style scoped></style>
