/**
 * 后端菜单（/base/usermenu，树）→ nova-admin 路由行（扁平 RowRoute）
 * - catalog → dir（无组件，挂在布局下）
 * - menu → page，component「/system/account」对应 src/views/system/account/index.vue
 * - 子菜单 path 为相对路径（如 account），拼接为完整路径 /system/account
 */
const BUILTIN: AppRoute.RowRoute[] = [
  {
    id: -1,
    pid: null,
    name: 'workbench',
    path: '/workbench',
    title: '工作台',
    icon: 'icon-park-outline:workbench',
    menuType: 'page',
    componentPath: '/dashboard/workbench/index.vue',
    pinTab: true,
    // nova 的排序把 0 当作未设置，用 -1 保证工作台排在最前
    order: -1,
    requiresAuth: true,
  },
  {
    id: -2,
    pid: null,
    name: 'userCenter',
    path: '/user-center',
    title: '个人中心',
    icon: 'icon-park-outline:user',
    menuType: 'page',
    componentPath: '/build-in/user-center/index.vue',
    hide: true,
    requiresAuth: true,
  },
]

function joinPath(parent: string, path: string) {
  if (path.startsWith('/'))
    return path
  return `${parent.replace(/\/$/, '')}/${path}`
}

const routeName = (path: string) => path.replace(/^\//, '').replace(/[/-]/g, '_') || 'root'

export function menusToRoutes(menus: Entity.Menu[]): AppRoute.RowRoute[] {
  const rows: AppRoute.RowRoute[] = [...BUILTIN]
  const walk = (items: Entity.Menu[], parent: { id: number, path: string } | null) => {
    for (const m of items) {
      const path = joinPath(parent?.path ?? '', m.path)
      const isDir = m.menu_type === 'catalog'
      rows.push({
        id: m.id,
        pid: parent?.id ?? null,
        name: routeName(path),
        path,
        title: m.name,
        href: m.href || undefined,
        icon: m.icon || undefined,
        order: m.order,
        hide: m.is_hidden,
        keepAlive: m.keepalive,
        menuType: isDir ? 'dir' : 'page',
        componentPath: isDir ? null : m.href ? '/build-in/iframe/index.vue' : `${m.component.replace(/\/$/, '')}/index.vue`,
        redirect: m.redirect || undefined,
        requiresAuth: true,
      })
      if (m.children?.length)
        walk(m.children, { id: m.id, path })
    }
  }
  walk(menus, null)
  return rows
}
