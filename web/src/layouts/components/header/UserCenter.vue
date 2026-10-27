<script setup lang="ts">
import { confirmDialog } from '@/utils'
import { startLogin } from '@/service'
import { useAuthStore, useTabStore } from '@/store'
import IconLogout from '~icons/icon-park-outline/logout'
import IconSwitch from '~icons/icon-park-outline/switch'
import IconUser from '~icons/icon-park-outline/user'

const { t } = useI18n()

const authStore = useAuthStore()
const router = useRouter()

const options = computed(() => {
  return [
    {
      label: t('app.userCenter'),
      key: 'userCenter',
      icon: () => h(IconUser),
    },
    // 切换租户 = 重新授权换取新 tid 的 Token（SSO 会话内免输密码）
    ...((authStore.userInfo?.tenants?.length ?? 0) > 1
      ? [{ label: '切换租户', key: 'switchTenant', icon: () => h(IconSwitch) }]
      : []),
    {
      type: 'divider',
      key: 'd1',
    },
    {
      label: t('app.loginOut'),
      key: 'loginOut',
      icon: () => h(IconLogout),
    },
  ]
})
function handleSelect(key: string | number) {
  if (key === 'loginOut') {
    confirmDialog({
      title: t('app.loginOutTitle'),
      content: t('app.loginOutContent'),
      onPositiveClick: () => {
        authStore.logout()
      },
    })
  }
  if (key === 'userCenter')
    router.push('/user-center')
  if (key === 'switchTenant') {
    // 标签页属于上一个租户的菜单
    useTabStore().clearAllTabs()
    startLogin({ silent: false, prompt: 'select_tenant', returnTo: '/' })
  }
}
</script>

<template>
  <n-dropdown
    trigger="click"
    :options="options"
    @select="handleSelect"
  >
    <n-avatar
      round
      class="cursor-pointer"
      :src="authStore.userInfo?.avatar"
    >
      <template #fallback>
        <div class="wh-full flex-center">
          <icon-park-outline-user />
        </div>
      </template>
    </n-avatar>
  </n-dropdown>
</template>

<style scoped></style>
