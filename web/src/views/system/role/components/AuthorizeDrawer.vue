<script setup lang="ts">
import { message } from '@/utils'
import type { TreeOption } from 'naive-ui'
import { fetchApiPage, fetchMenuTree, fetchRoleAuthorized, fetchUpdateRoleAuthorized } from '@/service'

const visible = ref(false)
const loading = ref(false)
const role = ref<Entity.Role>()
const menuTree = ref<Entity.Menu[]>([])
const apiTree = ref<TreeOption[]>([])
const menuIds = ref<number[]>([])
const apiKeys = ref<string[]>([])

const apiKey = (a: { method: string, path: string }) => `${a.method} ${a.path}`

// 接口按模块（tags）分组；叶子节点的 key 为「方法 路径」
function buildApiTree(apis: Entity.Api[]): TreeOption[] {
  const groups = new Map<string, TreeOption[]>()
  for (const a of apis) {
    const list = groups.get(a.tags) ?? []
    list.push({ key: apiKey(a), label: `${a.summary}  ${a.method} ${a.path}` })
    groups.set(a.tags, list)
  }
  return [...groups].map(([tag, children]) => ({ key: `tag:${tag}`, label: tag, children }))
}

async function open(row: Entity.Role) {
  role.value = row
  visible.value = true
  const [menus, apis, authorized] = await Promise.all([
    fetchMenuTree(),
    fetchApiPage({ page: 1, page_size: 9999 }),
    fetchRoleAuthorized(row.id),
  ])
  menuTree.value = menus.data ?? []
  apiTree.value = buildApiTree(apis.data ?? [])
  // 级联勾选下只回填叶子：角色拥有上级目录不代表拥有其全部子菜单
  const parentIds = new Set<number>()
  const walk = (items: Entity.Menu[]) => items.forEach((m) => {
    if (m.children?.length) {
      parentIds.add(m.id)
      walk(m.children)
    }
  })
  walk(menuTree.value)
  menuIds.value = authorized.data?.menus.map(m => m.id).filter(id => !parentIds.has(id)) ?? []
  apiKeys.value = authorized.data?.apis.map(apiKey) ?? []
}

async function submit() {
  loading.value = true
  const api_infos = apiKeys.value
    .filter(k => !k.startsWith('tag:'))
    .map((k) => {
      const [method, path] = k.split(' ')
      return { method, path }
    })
  // 后端按目录组织菜单：勾选的菜单连同其全部上级目录一起提交
  const parentOf = new Map<number, number>()
  const walk = (items: Entity.Menu[]) => items.forEach((m) => {
    m.children?.forEach(c => parentOf.set(c.id, m.id))
    walk(m.children ?? [])
  })
  walk(menuTree.value)
  const menu_ids = new Set<number>()
  for (let id of menuIds.value) {
    for (; id !== undefined; id = parentOf.get(id)!) menu_ids.add(id)
  }
  const res = await fetchUpdateRoleAuthorized({ id: role.value!.id, menu_ids: [...menu_ids], api_infos })
  loading.value = false
  if (res.isSuccess) {
    message.success('权限已更新')
    visible.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <n-drawer v-model:show="visible" :width="560">
    <n-drawer-content :title="`设置权限 · ${role?.name ?? ''}`" closable>
      <n-tabs type="line" animated>
        <n-tab-pane name="menu" tab="菜单">
          <n-tree
            v-model:checked-keys="menuIds"
            :data="menuTree"
            key-field="id"
            label-field="name"
            checkable
            cascade
            block-line
            default-expand-all
          />
        </n-tab-pane>
        <n-tab-pane name="api" tab="接口">
          <n-tree
            v-model:checked-keys="apiKeys"
            :data="apiTree"
            checkable
            cascade
            block-line
          />
        </n-tab-pane>
      </n-tabs>
      <template #footer>
        <n-space>
          <n-button @click="visible = false">
            取消
          </n-button>
          <n-button v-permission="'post/api/v1/role/authorized'" type="primary" :loading="loading" @click="submit">
            保存
          </n-button>
        </n-space>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>
