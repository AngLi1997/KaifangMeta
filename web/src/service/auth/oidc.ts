// 控制台作为 OIDC 客户端 kaifang-meta-console：授权码 + PKCE，经网关公开路由 /kaifang-meta/iam
import type { TokenSet } from './token'
import { session } from '@/utils'
import { getRefreshToken, removeToken, setToken } from './token'

const IAM = '/kaifang-meta/iam'
const CLIENT_ID = import.meta.env.CONSOLE_CLIENT_ID
// Access Token 剩余 2 分钟时主动续期（docs/auth-flow.md「Token 续期」）
const REFRESH_AHEAD_SECONDS = 120

let refreshTimer: ReturnType<typeof setTimeout> | undefined
let refreshing: Promise<void> | null = null

const redirectUri = () => `${location.origin}/auth/callback`

function base64url(buf: ArrayBuffer | Uint8Array) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

const randomString = (bytes = 32) => base64url(crypto.getRandomValues(new Uint8Array(bytes)))

async function challengeOf(verifier: string) {
  return base64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)))
}

async function requestToken(body: Record<string, string>): Promise<TokenSet> {
  const res = await fetch(`${IAM}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...body }),
  })
  if (!res.ok)
    throw new Error((await res.json().catch(() => ({}))).error || `token ${res.status}`)
  return res.json()
}

function saveTokens(value: TokenSet) {
  setToken(value)
  clearTimeout(refreshTimer)
  const delay = Math.max(value.expires_in - REFRESH_AHEAD_SECONDS, 10) * 1000
  // 续期失败不处理：下一次请求 401 时再续期或重新登录
  refreshTimer = setTimeout(() => refreshToken().catch(() => {}), delay)
}

/** 整页跳转到认证模块；silent 时带 prompt=none，SSO 会话有效则无登录页；prompt=select_tenant 用于切换租户 */
export async function startLogin({ silent = true, returnTo = location.pathname + location.search, prompt = '' } = {}) {
  const verifier = randomString()
  const state = randomString(16)
  session.set('oidcPending', { verifier, state, returnTo })
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    code_challenge: await challengeOf(verifier),
    code_challenge_method: 'S256',
    state,
  })
  if (silent)
    params.set('prompt', 'none')
  else if (prompt)
    params.set('prompt', prompt)
  location.assign(`${IAM}/authorize?${params}`)
}

/** 回调页：换 Token，返回登录前的页面地址；需要显式登录时返回 null 并已发起跳转 */
export async function handleCallback(query: Record<string, string | undefined>) {
  const pending = session.get('oidcPending')
  session.remove('oidcPending')
  if (query.error === 'login_required') {
    await startLogin({ silent: false, returnTo: pending?.returnTo || '/' })
    return null
  }
  if (!pending || query.state !== pending.state || !query.code)
    throw new Error(query.error || '登录状态校验失败')
  saveTokens(await requestToken({
    grant_type: 'authorization_code',
    code: query.code,
    redirect_uri: redirectUri(),
    code_verifier: pending.verifier,
  }))
  return pending.returnTo || '/'
}

/** Refresh Token 一次一用，并发请求共用同一次续期 */
export function refreshToken() {
  const refresh_token = getRefreshToken()
  if (!refresh_token)
    return Promise.reject(new Error('no refresh token'))
  refreshing ??= requestToken({ grant_type: 'refresh_token', refresh_token })
    .then(saveTokens)
    .finally(() => (refreshing = null))
  return refreshing
}

export function logout() {
  clearTimeout(refreshTimer)
  removeToken()
  const params = new URLSearchParams({ client_id: CLIENT_ID, post_logout_redirect_uri: `${location.origin}/` })
  location.assign(`${IAM}/logout?${params}`)
}
