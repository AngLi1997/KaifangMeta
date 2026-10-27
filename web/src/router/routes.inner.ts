import type { RouteRecordRaw } from 'vue-router'

/* 固定路由：OIDC 回调、错误页（登录页由认证模块提供） */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'root',
    children: [],
  },
  {
    path: '/auth/callback',
    name: 'authCallback',
    component: () => import('@/views/build-in/auth-callback/index.vue'),
    meta: {
      title: '登录中',
      requiresAuth: false,
      withoutTab: true,
    },
  },
  {
    path: '/not-found',
    name: 'not-found',
    component: () => import('@/views/build-in/not-found/index.vue'),
    meta: {
      title: '找不到页面',
      icon: 'icon-park-outline:ghost',
      withoutTab: true,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/build-in/not-found/index.vue'),
    name: 'not-found',
    meta: {
      title: '找不到页面',
      icon: 'icon-park-outline:ghost',
      withoutTab: true,
    },
  },
]
