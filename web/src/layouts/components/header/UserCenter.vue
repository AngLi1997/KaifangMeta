<script setup lang="ts">
import { confirmDialog } from '@/utils'
import { startLogin } from '@/service'
import { useAuthStore, useTabStore } from '@/store'
import IconLogout from '~icons/icon-park-outline/logout'
import IconSwitch from '~icons/icon-park-outline/switch'
import IconUser from '~icons/icon-park-outline/user'

// 控制台布局与统一门户共用：门户用户可能不是控制台成员，资料由调用方传入
const props = defineProps<{
  name: string
  avatar?: string
  tenantId?: string
  tenants?: { id: string, name: string }[]
  /** 个人中心属于控制台，非成员不显示 */
  showUserCenter?: boolean
}>()

const { t } = useI18n()

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const options = computed(() => {
  return [
    ...(props.showUserCenter
      ? [{ label: t('app.userCenter'), key: 'userCenter', icon: () => h(IconUser) }]
      : []),
    // 切换租户 = 带 tenant 重新授权换取新 tid 的 Token（SSO 会话内免输密码）
    ...((props.tenants?.length ?? 0) > 1
      ? [{
          label: t('app.switchTenant'),
          key: 'switchTenant',
          icon: () => h(IconSwitch),
          children: props.tenants!.map(item => ({ label: item.name, key: `tenant:${item.id}`, disabled: item.id === props.tenantId })),
        }]
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
  if (String(key).startsWith('tenant:')) {
    // 标签页与菜单属于上一个租户：门户内切换回门户，控制台内切换回首页
    useTabStore().clearAllTabs()
    startLogin({ tenant: String(key).slice('tenant:'.length), returnTo: route.name === 'portal' ? '/portal' : import.meta.env.VITE_HOME_PATH })
  }
}
</script>

<template>
  <n-dropdown
    trigger="click"
    :options="options"
    @select="handleSelect"
  >
    <n-el class="user-pill">
      <!-- 有默认插槽时 n-avatar 不显示 src，图片与首字母分开渲染 -->
      <n-avatar v-if="avatar" round :size="34" :src="avatar" />
      <n-avatar v-else round :size="34" color="var(--primary-color)">
        {{ name.slice(0, 1).toUpperCase() }}
      </n-avatar>
      <span class="whitespace-nowrap">{{ name }}</span>
      <icon-park-outline-down class="text-[var(--text-color-3)]" />
    </n-el>
  </n-dropdown>
</template>

<style scoped>
.user-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 8px;
  padding: 3px 12px 3px 3px;
  border-radius: 40px;
  background: var(--card-color);
  box-shadow: var(--box-shadow-1);
  cursor: pointer;
}
</style>
