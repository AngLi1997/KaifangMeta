<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchUpdatePassword, fetchUploadAvatar } from '@/service'
import { useAuthStore } from '@/store'

const authStore = useAuthStore()
const user = computed(() => authStore.userInfo)

const formRef = ref<FormInst | null>(null)
const avatarInput = ref<HTMLInputElement | null>(null)
const loading = ref(false)
const avatarLoading = ref(false)
const form = ref({ old_password: '', new_password: '', confirm_password: '' })
const rules: FormRules = {
  old_password: { required: true, message: '请输入旧密码', trigger: 'blur' },
  new_password: { required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  confirm_password: {
    required: true,
    trigger: ['blur', 'input'],
    validator: (_, value: string) => value === form.value.new_password || new Error('两次输入的密码不一致'),
  },
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  const res = await fetchUpdatePassword(form.value)
  loading.value = false
  if (res.isSuccess) {
    message.success('密码已修改')
    form.value = { old_password: '', new_password: '', confirm_password: '' }
  }
}

async function uploadAvatar(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file)
    return

  avatarLoading.value = true
  try {
    const data = new FormData()
    data.append('file', file)
    const res = await fetchUploadAvatar(data)
    if (res.isSuccess && authStore.userInfo && res.data?.avatar) {
      authStore.userInfo.avatar = res.data.avatar
      message.success('头像已更新')
    }
  }
  finally {
    avatarLoading.value = false
    input.value = ''
  }
}
</script>

<template>
  <n-space vertical :size="16">
    <n-card title="个人信息">
      <n-space align="center" class="mb-4">
        <n-avatar round :size="64" :src="user?.avatar" />
        <n-button type="primary" :loading="avatarLoading" @click="avatarInput?.click()">
          上传头像
        </n-button>
        <input
          ref="avatarInput" class="hidden" type="file" accept="image/jpeg,image/png,image/webp"
          @change="uploadAvatar"
        >
      </n-space>
      <n-descriptions label-placement="left" :column="2" bordered>
        <n-descriptions-item label="用户名">
          {{ user?.username }}
        </n-descriptions-item>
        <n-descriptions-item label="姓名">
          {{ user?.alias || '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="邮箱">
          {{ user?.email }}
        </n-descriptions-item>
        <n-descriptions-item label="电话">
          {{ user?.phone || '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="身份账号">
          <copy-text :value="user?.sub ?? ''" />
        </n-descriptions-item>
        <n-descriptions-item label="最近访问">
          {{ user?.last_login }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-card title="修改密码">
      <n-form ref="formRef" class="max-w-480px" :model="form" :rules="rules" label-placement="left" :label-width="90">
        <n-form-item label="旧密码" path="old_password">
          <n-input v-model:value="form.old_password" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item label="新密码" path="new_password">
          <n-input v-model:value="form.new_password" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item label="确认密码" path="confirm_password">
          <n-input v-model:value="form.confirm_password" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item label=" ">
          <n-button type="primary" :loading="loading" @click="submit">
            保存
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>
  </n-space>
</template>
