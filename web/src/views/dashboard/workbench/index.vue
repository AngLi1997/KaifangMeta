<script setup lang="ts">
import { fetchAccountPage, fetchApiPage, fetchRolePage } from '@/service'
import { useAuthStore } from '@/store'
import { usePermission } from '@/hooks'

const authStore = useAuthStore()
const { hasPermission } = usePermission()
const router = useRouter()

const stats = ref([
  { label: '身份账号', icon: 'icon-park-outline:id-card', path: '/system/account', value: 0, load: fetchAccountPage },
  { label: '角色', icon: 'icon-park-outline:permissions', path: '/system/role', value: 0, load: fetchRolePage },
  { label: '接口', icon: 'icon-park-outline:api', path: '/system/api', value: 0, load: fetchApiPage },
])
const canListAccounts = computed(() => hasPermission('get/api/v1/account/list'))
const visibleStats = computed(() => stats.value.filter(item => item.label !== '身份账号' || canListAccounts.value))

const greeting = computed(() => {
  const hour = new Date().getHours()
  return hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'
})

onMounted(() => {
  stats.value.forEach(async (item) => {
    if (item.label === '身份账号' && !canListAccounts.value)
      return
    const res = await item.load({ page: 1, page_size: 1 })
    if (res.isSuccess)
      item.value = res.total
  })
})
</script>

<template>
  <n-space vertical :size="16">
    <n-card>
      <n-thing>
        <template #avatar>
          <n-avatar round :size="56" :src="authStore.userInfo?.avatar">
            <template #fallback>
              <div class="wh-full flex-center">
                <icon-park-outline-user class="text-28px" />
              </div>
            </template>
          </n-avatar>
        </template>
        <template #header>
          {{ greeting }}，{{ authStore.userInfo?.alias || authStore.userInfo?.username }}
        </template>
        <template #description>
          <n-text depth="3">
            {{ authStore.userInfo?.sub }}
          </n-text>
        </template>
      </n-thing>
    </n-card>

    <n-grid :x-gap="16" :y-gap="16" cols="1 s:2 l:4" responsive="screen">
      <n-gi v-for="item in visibleStats" :key="item.label">
        <n-card hoverable class="cursor-pointer" @click="router.push(item.path)">
          <n-thing>
            <template #avatar>
              <n-icon-wrapper :size="46" color="var(--primary-color)" :border-radius="999">
                <nova-icon :size="26" :icon="item.icon" />
              </n-icon-wrapper>
            </template>
            <template #header>
              <n-statistic :label="item.label">
                <n-number-animation show-separator :from="0" :to="item.value" />
              </n-statistic>
            </template>
          </n-thing>
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
</template>
