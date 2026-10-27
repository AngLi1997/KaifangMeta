<script setup lang="ts">
const route = useRoute()
</script>

<template>
  <n-card class="h-full" content-class="p-0!">
    <iframe :src="route.meta.href" class="block h-full w-full border-0" />
  </n-card>
</template>
