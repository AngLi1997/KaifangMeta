<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateAccount, fetchTenantPage, fetchUpdateAccount } from '@/service'
import { useAuthStore } from '@/store'

type Form = Entity.AccountForm & { sub?: string, is_console_admin?: boolean }
const emit = defineEmits<{ success: [] }>()
const authStore = useAuthStore()
const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const tenants = ref<Entity.Tenant[]>([])
const form = ref<Form>({ tenant_id: '', username: '', email: null, name: null, phone: null, password: '', status: 'active', member_tenant_ids: [] })
const originalStatus = ref<Entity.Account['status']>('active')
const tenantOptions = computed(() => tenants.value.map(tenant => ({
  label: `${tenant.name} · ${tenant.id}${tenant.status === 'disabled' ? '（停用）' : ''}`,
  value: tenant.id,
  disabled: tenant.status === 'disabled' && tenant.id !== form.value.tenant_id,
})))
// 跨租户成员只由系统租户管理；系统租户本身不作为成员租户
const memberOptions = computed(() => tenants.value
  .filter(tenant => tenant.id !== form.value.tenant_id && tenant.id !== authStore.userInfo?.tenant_id)
  .map(tenant => ({ label: tenant.name, value: tenant.id, disabled: tenant.status === 'disabled' && !form.value.member_tenant_ids?.includes(tenant.id) })))
const statusOptions = computed(() => [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled', disabled: form.value.is_console_admin },
])
const rules: FormRules = {
  tenant_id: { required: true, message: '请选择租户', trigger: 'change' },
  username: { required: true, message: '请输入登录名', trigger: 'blur' },
  email: { type: 'email', message: '请输入有效邮箱', trigger: 'blur' },
  password: {
    validator: (_rule, value) => form.value.sub ? !value || value.length >= 8 : Boolean(value) && value.length >= 8,
    message: '新密码至少 8 位',
    trigger: 'blur',
  },
}

async function open(row?: Entity.IdentityAccount) {
  const result = await fetchTenantPage({ page: 1, page_size: 500 })
  tenants.value = result.data ?? []
  originalStatus.value = row?.status ?? 'active'
  form.value = row
    ? {
        sub: row.sub,
        is_console_admin: row.console_member?.is_superuser,
        tenant_id: row.tenant_id,
        username: row.username,
        email: row.email,
        name: row.name,
        phone: row.phone,
        password: '',
        status: row.status,
        member_tenant_ids: row.member_tenants?.map(tenant => tenant.id) ?? [],
      }
    : {
        tenant_id: tenants.value.find(tenant => tenant.status === 'active')?.id ?? '',
        username: '',
        email: null,
        name: null,
        phone: null,
        password: '',
        status: 'active',
        member_tenant_ids: [],
      }
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const { sub, tenant_id, username, email, name, phone, password, status, member_tenant_ids } = form.value
  const identity = {
    tenant_id,
    username,
    email: email || null,
    name: name || null,
    phone: phone || null,
    ...(authStore.isSystemTenant ? { member_tenant_ids: member_tenant_ids?.filter(id => id !== tenant_id) } : {}),
  }
  const res = sub
    ? await fetchUpdateAccount({ ...identity, sub, status, ...(password ? { password } : {}) })
    : await fetchCreateAccount({ ...identity, password: password! })
  loading.value = false
  if (res.isSuccess) {
    message.success('已保存')
    visible.value = false
    emit('success')
  }
}

defineExpose({ open })
</script>

<template>
  <FormModal
    v-model:show="visible"
    :title="form.sub ? '编辑身份账号' : '新建身份账号'"
    :loading="loading"
    :confirm="form.sub && originalStatus === 'active' && form.status === 'disabled' ? '停用后，该身份账号将无法登录。' : undefined"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="88">
      <n-form-item v-if="form.sub" label="sub">
        <n-input :value="form.sub" readonly />
      </n-form-item>
      <n-form-item label="登录名" path="username">
        <n-input v-model:value="form.username" :maxlength="64" />
      </n-form-item>
      <n-form-item label="姓名" path="name">
        <n-input v-model:value="form.name" clearable :maxlength="64" />
      </n-form-item>
      <n-form-item label="电话" path="phone">
        <n-input v-model:value="form.phone" clearable :maxlength="20" />
      </n-form-item>
      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="form.email" clearable />
      </n-form-item>
      <n-form-item label="租户" path="tenant_id">
        <n-select v-model:value="form.tenant_id" :options="tenantOptions" :disabled="form.is_console_admin || !authStore.isSystemTenant" />
      </n-form-item>
      <n-form-item v-if="authStore.isSystemTenant && !form.is_console_admin" label="其他租户">
        <n-select v-model:value="form.member_tenant_ids" multiple clearable :options="memberOptions" />
      </n-form-item>
      <n-form-item :label="form.sub ? '新密码' : '初始密码'" path="password">
        <n-input v-model:value="form.password" type="password" show-password-on="click" autocomplete="new-password" />
      </n-form-item>
      <n-form-item v-if="form.sub" label="状态" path="status">
        <n-select v-model:value="form.status" :options="statusOptions" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
