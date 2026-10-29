<script setup lang="ts">
import { useAppStore } from '@/store'

// 门户页没有侧栏，始终显示名称
const props = defineProps<{ showText?: boolean }>()
const router = useRouter()
const appStore = useAppStore()

const name = import.meta.env.APP_TITLE
const logo = '/kaifangdata-logo.png'

const hidenLogoText = computed(() => {
  if (props.showText)
    return false
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
    class="h-60px flex-center cursor-pointer gap-3 p-x-2"
    @click="router.push('/')"
  >
    <img :src="logo" alt="" class="h-8 w-8 shrink-0 object-contain">
    <span
      v-show="!hidenLogoText"
      class="text-5 font-bold text-ellipsis overflow-hidden whitespace-nowrap"
    >{{ name }}</span>
  </div>
</template>

<style scoped></style>
