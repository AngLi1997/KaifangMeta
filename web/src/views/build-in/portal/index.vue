<script setup lang="ts">
import { FullScreen, Logo, Setting, SettingDrawer, UserCenter } from '@/layouts/components'
import { fetchPortalApps } from '@/service'
import { useAppStore } from '@/store'

const CONSOLE_CLIENT_ID = import.meta.env.CONSOLE_CLIENT_ID
const router = useRouter()
const appStore = useAppStore()

const loading = ref(true)
const info = ref<Api.Portal.Info>()
const keyword = ref('')

onMounted(async () => {
  const res = await fetchPortalApps()
  if (res.isSuccess)
    info.value = res.data
  loading.value = false
})

const userName = computed(() => info.value?.user.name || info.value?.user.username || '')
const apps = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  return (info.value?.apps ?? []).filter(a => !k || `${a.name}${a.description ?? ''}`.toLowerCase().includes(k))
})
// 控制台磁贴只对控制台成员返回，据此决定是否显示个人中心
const isConsoleMember = computed(() => info.value?.apps.some(a => a.client_id === CONSOLE_CLIENT_ID))

function open(app: Api.Portal.App) {
  if (app.status === 'disabled')
    return
  // 控制台与门户同一前端；其他应用整页跳转，由其前端壳 prompt=none 静默登录
  if (app.client_id === CONSOLE_CLIENT_ID)
    router.push(import.meta.env.VITE_HOME_PATH)
  else
    location.assign(app.entry)
}
</script>

<template>
  <!-- n-el 注入主题 CSS 变量：门户在控制台布局之外，强调色随设置的主题主色变化 -->
  <n-el class="portal">
    <SettingDrawer />
    <!-- 与控制台导航栏同一套组件与尺寸：Logo、搜索、全屏 / 主题 / 语言 / 设置、用户 -->
    <header class="top-bar">
      <Logo show-text />
      <div class="h-full flex-y-center gap-1">
        <template v-if="!appStore.isMobile">
          <n-input v-model:value="keyword" round clearable class="w-60!" :placeholder="$t('app.searchApp')">
            <template #prefix>
              <icon-park-outline-search />
            </template>
          </n-input>
          <FullScreen />
          <DarkModeSwitch />
          <LangsSwitch />
          <Setting />
        </template>
        <UserCenter
          :name="userName"
          :avatar="info?.user.avatar"
          :tenant-id="info?.tenant_id"
          :tenants="info?.tenants"
          :show-user-center="isConsoleMember"
        />
      </div>
    </header>

    <main class="main">
      <div class="flex-y-center gap-2 mb-10 text-8 font-bold">
        <icon-park-outline-hand-right class="text-[var(--primary-color)]" />
        {{ $t('app.welcomeBack', { name: userName }) }}
      </div>
      <n-spin :show="loading">
        <div v-if="apps.length" class="grid">
          <div v-for="app in apps" :key="app.client_id" class="card" :class="{ disabled: app.status === 'disabled' }" @click="open(app)">
            <div class="card-icon">
              {{ app.icon || app.name.slice(0, 1) }}
            </div>
            <div class="card-title">
              {{ app.name }}
              <n-tag v-if="app.status === 'disabled'" size="small" :bordered="false">
                {{ $t('app.maintenance') }}
              </n-tag>
              <icon-park-outline-arrow-right v-else class="arrow" />
            </div>
            <div class="text-[var(--text-color-2)]">
              {{ app.description }}
            </div>
          </div>
        </div>
        <n-empty
          v-else-if="!loading"
          class="py-20"
          :description="keyword ? $t('app.noMatchApps') : $t('app.noApps')"
        />
      </n-spin>
    </main>
  </n-el>
</template>

<style scoped>
.portal {
  min-height: 100%;
  background: var(--body-color);
  color: var(--text-color-1);
}

.top-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 20px 0 16px;
  background: var(--card-color);
  border-bottom: 1px solid var(--divider-color);
}

.main {
  max-width: 1500px;
  margin: 0 auto;
  padding: 40px 5% 48px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 28px;
}

.card {
  display: flex;
  flex-direction: column;
  padding: 28px 24px 24px;
  border-radius: 28px;
  border: 1px solid var(--divider-color);
  background: var(--card-color);
  box-shadow: var(--box-shadow-1);
  cursor: pointer;
  transition:
    transform 0.25s cubic-bezier(0.2, 0, 0, 1),
    box-shadow 0.3s,
    border-color 0.3s;
}

.card.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.card:not(.disabled):hover {
  transform: translateY(-6px);
  box-shadow: var(--box-shadow-3);
  border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
}

.card-icon {
  width: 60px;
  height: 60px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  font-size: 22px;
  font-weight: 700;
  color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 12%, transparent);
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 20px;
  font-weight: 700;
}

.arrow {
  font-size: 16px;
  color: var(--text-color-3);
  transition: transform 0.2s;
}

.card:not(.disabled):hover .arrow {
  transform: translateX(4px);
  color: var(--primary-color);
}
</style>
