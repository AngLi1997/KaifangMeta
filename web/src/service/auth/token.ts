// Token 只存内存，不写 localStorage（docs/auth-flow.md）；页面刷新后经 prompt=none 静默恢复
export interface TokenSet {
  access_token: string
  refresh_token?: string
  expires_in: number
  token_type: string
}

let tokens: TokenSet | null = null

export const getToken = () => tokens?.access_token
export const getRefreshToken = () => tokens?.refresh_token
export const setToken = (value: TokenSet) => (tokens = value)
export const removeToken = () => (tokens = null)
