<script setup lang="ts">
import { message } from '@/utils'
import { useAuthStore } from '@/store'
import { fetchRolePage, fetchUpdateMemberRoles } from '@/service'

const emit = defineEmits<{ success: [] }>()
const authStore = useAuthStore()
const visible = ref(false)
const loading = ref(false)
const account = ref<Entity.IdentityAccount>()
const roles = ref<Entity.Role[]>([])
const tenantId = ref('')
const roleIds = ref<number[]>([])

// 系统角色只在系统租户授予；只有系统租户的管理员能选择租户
const systemTenantId = computed(() => authStore.isSystemTenant ? authStore.userInfo!.tenant_id : '')
const tenantOptions = computed(() => account.value
  ? [{ id: account.value.tenant_id, name: account.value.tenant_name ?? account.value.tenant_id }, ...(account.value.member_tenants ?? [])]
      .map(tenant => ({ label: tenant.name, value: tenant.id }))
  : [])
const roleOptions = computed(() => roles.value
  .filter(role => (role.scope === 'system') === (tenantId.value === systemTenantId.value))
  .map(role => ({ label: role.name, value: role.id })))

function bound(tenant: string) {
  return (account.value?.console_member?.roles ?? []).filter(role => role.tenant_id === tenant).map(role => role.id)
}

async function open(row: Entity.IdentityAccount) {
  roles.value = (await fetchRolePage({ page: 1, page_size: 500 })).data ?? []
  account.value = row
  tenantId.value = authStore.isSystemTenant ? row.tenant_id : authStore.userInfo!.tenant_id
  roleIds.value = bound(tenantId.value)
  visible.value = true
}

function changeTenant(value: string) {
  tenantId.value = value
  roleIds.value = bound(value)
}

async function submit() {
  loading.value = true
  const res = await fetchUpdateMemberRoles({ sub: account.value!.sub, tenant_id: tenantId.value, role_ids: roleIds.value })
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
    :title="`控制台角色 · ${account?.username}`"
    size="sm"
    :loading="loading"
    @submit="submit"
  >
    <n-form label-placement="left" :label-width="70">
      <n-form-item v-if="authStore.isSystemTenant" label="租户">
        <n-select :value="tenantId" :options="tenantOptions" @update:value="changeTenant" />
      </n-form-item>
      <n-form-item label="角色">
        <n-select v-model:value="roleIds" multiple clearable :options="roleOptions" />
      </n-form-item>
    </n-form>
  </FormModal>
</template>
