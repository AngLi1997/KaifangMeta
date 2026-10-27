<script setup lang="ts">
import { message } from '@/utils'
import type { FormInst, FormRules } from 'naive-ui'
import { fetchCreateMenu, fetchUpdateMenu } from '@/service'

const props = defineProps<{ tree: Entity.Menu[] }>()
const emit = defineEmits<{ success: [] }>()

const visible = ref(false)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)

function defaults(): Partial<Entity.Menu> {
  return {
    menu_type: 'menu',
    parent_id: 0,
    name: '',
    path: '',
    href: '',
    component: '',
    icon: '',
    order: 1,
    is_hidden: false,
    keepalive: false,
    redirect: '',
  }
}
const form = ref(defaults())
const isCatalog = computed(() => form.value.menu_type === 'catalog')

// 上级只能是目录；0 为根
const parentOptions = computed(() => {
  const toOption = (m: Entity.Menu): any => ({
    key: m.id,
    label: m.name,
    children: m.children?.filter(c => c.menu_type === 'catalog').map(toOption),
  })
  return [{ key: 0, label: '根目录' }, ...props.tree.filter(m => m.menu_type === 'catalog').map(toOption)]
})

const rules = computed<FormRules>(() => ({
  name: { required: true, message: '请输入名称', trigger: 'blur' },
  path: { required: true, message: '请输入路由路径', trigger: 'blur' },
  ...(!form.value.href ? { component: { required: true, message: '请输入组件路径，如 /system/account', trigger: 'blur' } } : {}),
}))

function open(row?: Entity.Menu, parent?: Entity.Menu) {
  form.value = row ? { ...row, href: row.href ?? '' } : { ...defaults(), parent_id: parent?.id ?? 0 }
  delete form.value.children
  visible.value = true
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  // 目录由布局承载，组件固定为 Layout
  const data = {
    ...form.value,
    href: isCatalog.value ? null : form.value.href || null,
    component: isCatalog.value ? 'Layout' : form.value.href ? '' : form.value.component,
  }
  const res = data.id ? await fetchUpdateMenu(data) : await fetchCreateMenu(data)
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
    :title="form.id ? '编辑菜单' : '新建菜单'"
    size="lg"
    :loading="loading"
    @submit="submit"
  >
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="90">
      <n-grid :cols="2" :x-gap="18">
        <n-form-item-gi label="类型" path="menu_type">
          <n-radio-group v-model:value="form.menu_type">
            <n-radio-button value="catalog">
              目录
            </n-radio-button>
            <n-radio-button value="menu">
              菜单
            </n-radio-button>
          </n-radio-group>
        </n-form-item-gi>
        <n-form-item-gi label="上级" path="parent_id">
          <n-tree-select v-model:value="form.parent_id" :options="parentOptions" default-expand-all />
        </n-form-item-gi>
        <n-form-item-gi label="名称" path="name">
          <n-input v-model:value="form.name" />
        </n-form-item-gi>
        <n-form-item-gi label="图标" path="icon">
          <IconSelect :value="form.icon ?? undefined" @update:value="(v?: string) => (form.icon = v)" />
        </n-form-item-gi>
        <n-form-item-gi label="路由路径" path="path">
          <n-input v-model:value="form.path" :placeholder="form.parent_id ? '相对上级，如 user' : '如 /system'" />
        </n-form-item-gi>
        <n-form-item-gi v-if="!isCatalog" label="内嵌地址" path="href">
          <n-input v-model:value="form.href" placeholder="https://...（留空则使用页面组件）" />
        </n-form-item-gi>
        <n-form-item-gi v-if="!isCatalog && !form.href" label="组件" path="component">
          <n-input v-model:value="form.component" placeholder="src/views 下的目录，如 /system/account" />
        </n-form-item-gi>
        <n-form-item-gi v-else label="重定向" path="redirect">
          <n-input v-model:value="form.redirect" />
        </n-form-item-gi>
        <n-form-item-gi label="排序" path="order">
          <n-input-number v-model:value="form.order" :min="0" class="w-full" />
        </n-form-item-gi>
        <n-form-item-gi label="隐藏" path="is_hidden">
          <n-switch v-model:value="form.is_hidden" />
        </n-form-item-gi>
        <n-form-item-gi v-if="!isCatalog" label="页面缓存" path="keepalive">
          <n-switch v-model:value="form.keepalive" />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </FormModal>
</template>
