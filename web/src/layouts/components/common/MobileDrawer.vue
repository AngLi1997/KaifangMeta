<script setup lang="ts">
import Search from '../header/Search.vue'
import UserCenter from '../header/UserCenter.vue'
import Setting from './Setting.vue'
import { useAuthStore } from '@/store'

const showDrawer = defineModel<boolean>('show', { default: false })
const authStore = useAuthStore()
</script>

<template>
  <n-drawer
    v-model:show="showDrawer"
    :width="280"
    placement="right"
    :mask-closable="true"
    :close-on-esc="true"
  >
    <n-drawer-content :native-scrollbar="false" :body-content-style="{ padding: '0' }">
      <template #header>
        <div class="flex flex-col items-start gap-3">
          <UserCenter
            :name="authStore.userInfo?.alias || authStore.userInfo?.username || ''"
            :avatar="authStore.userInfo?.avatar"
            :tenant-id="authStore.userInfo?.tenant_id"
            :tenants="authStore.userInfo?.tenants"
            show-user-center
          />
          <Search />
        </div>
      </template>

      <slot />

      <template #footer>
        <DarkModeSwitch />
        <LangsSwitch />
        <div class="ml-auto" />
        <Setting />
      </template>
    </n-drawer-content>
  </n-drawer>
</template>
