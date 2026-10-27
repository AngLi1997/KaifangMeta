/* 存放数据库实体表类型， 具体内容在 ./entities */
declare namespace Entity {
}

/* 各类接口返回的数据类型， 具体内容在 ./api */
declare namespace Api {

}

interface Window {
  $loadingBar: import('naive-ui').LoadingBarApi
  $dialog: import('naive-ui').DialogApi
  $message: import('naive-ui').MessageApi
  $notification: import('naive-ui').NotificationApi
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent
  export default component
}

declare namespace NaiveUI {
  type ThemeColor = 'default' | 'error' | 'primary' | 'info' | 'success' | 'warning'
}

declare namespace Storage {
  interface Session {
    /* OIDC 授权跳转中的 PKCE 校验串与 state（仅本标签页、本次跳转） */
    oidcPending: { verifier: string, state: string, returnTo: string }
  }

  /* Token 只存内存，不写本地存储（docs/auth-flow.md） */
  interface Local {
    /* 存储当前语言 */
    lang: App.lang
  }
}

declare namespace App {
  type lang = 'zhCN' | 'enUS'
}
