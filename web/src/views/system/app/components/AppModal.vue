<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateApp, fetchTenantPage, fetchUpdateApp } from '@/service'

const emit = defineEmits<{ success: [], secrets: [clientId: string, secrets: Entity.AppSecrets] }>()
const visible = ref(false)
const loading = ref(false)
const editing = ref(false)
const tab = ref('basic')
const formRef = ref<FormInst | null>(null)
const tenants = ref<Entity.Tenant[]>([])
const tenantOptions = computed(() => tenants.value.map(t => ({ label: t.name, value: t.id, disabled: t.status === 'disabled' })))
const scopeOptions = ['directory:read', 'delegate:user'].map(value => ({ label: value, value }))

interface Form {
  client_id: string
  name: string
  owner: string | null
  tenants: string[]
  scopes: string[]
  redirect_uris: string[]
  post_logout_redirect_uris: string[]
  useGateway: boolean
  gateway: Entity.AppGateway
  portal: Required<Entity.AppPortal>
}

function defaults(): Form {
  return {
    client_id: 'kaifang-meta-',
    name: '',
    owner: null,
    tenants: [],
    scopes: ['directory:read'],
    redirect_uris: [],
    post_logout_redirect_uris: [],
    useGateway: true,
    gateway: { prefix: '/kaifang-meta/', routes: [{ path: '', nodes: [], health: null }], public_paths: [], rate_limit: 200 },
    portal: { entry: '', icon: '', description: '', order: 100 },
  }
}
const form = ref<Form>(defaults())
const newRoute = () => ({ path: '', nodes: [], health: null })

const rules: FormRules = {
  client_id: { required: true, pattern: /^kaifang-meta-[a-z0-9-]+$/, message: '以 kaifang-meta- 开头，小写字母、数字与连字符', trigger: 'blur' },
  name: { required: true, message: '请输入名称', trigger: 'blur' },
  tenants: { type: 'array', required: true, min: 1, message: '至少开通一个租户', trigger: 'change' },
}

async function open(row?: Entity.App) {
  tenants.value = (await fetchTenantPage({ page: 1, page_size: 500 })).data ?? []
  editing.value = Boolean(row)
  tab.value = 'basic'
  const base = defaults()
  form.value = row
    ? {
        client_id: row.client_id,
        name: row.name,
        owner: row.owner,
        tenants: [...row.tenants],
        scopes: [...row.scopes],
        redirect_uris: [...row.redirect_uris],
        post_logout_redirect_uris: [...row.post_logout_redirect_uris],
        useGateway: Boolean(row.gateway?.prefix),
        gateway: row.gateway?.prefix ? structuredClone(toRaw(row.gateway)) as Entity.AppGateway : base.gateway,
        portal: { ...base.portal, ...row.portal },
      }
    : { ...base, tenants: tenants.value.filter(t => t.status === 'active').slice(0, 1).map(t => t.id) }
  visible.value = true
}

async function submit() {
  try {
    await formRef.value?.validate()
  }
  catch {
    tab.value = 'basic'
    return
  }
  const { useGateway, gateway, portal, ...rest } = form.value
  const routes = gateway.routes.filter(r => r.path)
  if (useGateway && !routes.length) {
    tab.value = 'gateway'
    message.warning('请至少配置一条路由')
    return
  }
  loading.value = true
  const data = {
    ...rest,
    owner: rest.owner || null,
    redirect_uris: rest.redirect_uris.filter(Boolean),
    post_logout_redirect_uris: rest.post_logout_redirect_uris.filter(Boolean),
    gateway: useGateway ? { ...gateway, routes, public_paths: gateway.public_paths.filter(Boolean) } : null,
    portal,
  }
  const res = editing.value ? await fetchUpdateApp(data) : await fetchCreateApp(data)
  loading.value = false
  if (res.isSuccess) {
    message.success('已保存')
    visible.value = false
    emit('success')
    if (Object.keys(res.data.secrets).length)
      emit('secrets', data.client_id, res.data.secrets)
  }
}

defineExpose({ open })
</script>

<template>
  <FormModal v-model:show="visible" :title="editing ? '编辑应用' : '注册应用'" size="lg" :loading="loading" @submit="submit">
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="90">
      <n-tabs v-model:value="tab" type="line" animated>
        <n-tab-pane name="basic" tab="基本">
          <n-form-item label="client_id" path="client_id">
            <n-input v-model:value="form.client_id" :disabled="editing" :maxlength="64" />
          </n-form-item>
          <n-form-item label="名称" path="name">
            <n-input v-model:value="form.name" :maxlength="64" />
          </n-form-item>
          <n-form-item label="负责人" path="owner">
            <n-input v-model:value="form.owner" clearable :maxlength="64" />
          </n-form-item>
          <n-form-item label="开通租户" path="tenants">
            <n-select v-model:value="form.tenants" multiple :options="tenantOptions" />
          </n-form-item>
          <n-form-item label="平台权限" path="scopes">
            <n-select v-model:value="form.scopes" multiple tag :options="scopeOptions" />
          </n-form-item>
        </n-tab-pane>

        <n-tab-pane name="login" tab="登录">
          <n-form-item label="回调地址">
            <n-dynamic-input v-model:value="form.redirect_uris" placeholder="https://app.internal/auth/callback" />
          </n-form-item>
          <n-form-item label="退出回调">
            <n-dynamic-input v-model:value="form.post_logout_redirect_uris" placeholder="https://app.internal/" />
          </n-form-item>
        </n-tab-pane>

        <n-tab-pane name="gateway" tab="网关">
          <n-form-item label="经网关访问">
            <n-switch v-model:value="form.useGateway" />
          </n-form-item>
          <template v-if="form.useGateway">
            <n-form-item label="前缀">
              <n-input v-model:value="form.gateway.prefix" placeholder="/kaifang-meta/ub" />
            </n-form-item>
            <n-form-item label="路由">
              <n-dynamic-input v-model:value="form.gateway.routes" :on-create="newRoute">
                <template #default="{ value }">
                  <div class="w-full flex flex-col gap-2">
                    <div class="grid grid-cols-2 gap-2">
                      <n-input v-model:value="value.path" placeholder="子路径 /platform-common" />
                      <n-input v-model:value="value.health" clearable placeholder="健康检查 /platform-common/actuator/health" />
                    </div>
                    <n-dynamic-tags v-model:value="value.nodes">
                      <template #trigger="{ activate }">
                        <n-button size="small" dashed @click="activate()">
                          上游节点 IP:端口
                        </n-button>
                      </template>
                    </n-dynamic-tags>
                  </div>
                </template>
              </n-dynamic-input>
            </n-form-item>
            <n-form-item label="公开路径">
              <n-dynamic-input v-model:value="form.gateway.public_paths" placeholder="/platform-common/actuator/health" />
            </n-form-item>
            <n-form-item label="每租户 QPS">
              <n-input-number v-model:value="form.gateway.rate_limit" :min="1" class="w-40" />
            </n-form-item>
          </template>
        </n-tab-pane>

        <n-tab-pane name="portal" tab="门户">
          <n-form-item label="入口地址">
            <n-input v-model:value="form.portal.entry" clearable placeholder="不填则不在门户显示" />
          </n-form-item>
          <n-form-item label="图标">
            <n-input v-model:value="form.portal.icon" clearable :maxlength="2" class="w-24" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="form.portal.description" clearable :maxlength="64" />
          </n-form-item>
          <n-form-item label="排序">
            <n-input-number v-model:value="form.portal.order" :min="0" class="w-40" />
          </n-form-item>
        </n-tab-pane>
      </n-tabs>
    </n-form>
  </FormModal>
</template>
