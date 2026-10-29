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

// HTTP 局域网访问不是安全上下文，没有 crypto.subtle，退回纯 JS SHA-256
function sha256(msg: Uint8Array) {
  const primes: number[] = []
  for (let n = 2; primes.length < 64; n++) {
    if (primes.every(p => n % p))
      primes.push(n)
  }
  const frac = (x: number) => ((x - Math.floor(x)) * 2 ** 32) >>> 0
  const k = primes.map(p => frac(Math.cbrt(p)))
  const h = primes.slice(0, 8).map(p => frac(Math.sqrt(p)))
  const size = (msg.length + 72) & ~63
  const bytes = new Uint8Array(size)
  bytes.set(msg)
  bytes[msg.length] = 0x80
  const view = new DataView(bytes.buffer)
  view.setUint32(size - 4, msg.length * 8)
  const w = new Uint32Array(64)
  const rotr = (x: number, n: number) => (x >>> n) | (x << (32 - n))
  for (let off = 0; off < size; off += 64) {
    for (let i = 0; i < 64; i++) {
      w[i] = i < 16
        ? view.getUint32(off + i * 4)
        : w[i - 16] + (rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3))
          + w[i - 7] + (rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10))
    }
    const s = [...h]
    for (let i = 0; i < 64; i++) {
      const [a, b, c, d, e, f, g, hh] = s
      const t1 = (hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i]) | 0
      const t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0
      s.splice(0, 8, (t1 + t2) | 0, a, b, c, (d + t1) | 0, e, f, g)
    }
    s.forEach((x, i) => (h[i] = (h[i] + x) >>> 0))
  }
  const out = new DataView(new ArrayBuffer(32))
  h.forEach((x, i) => out.setUint32(i * 4, x))
  return new Uint8Array(out.buffer)
}

async function challengeOf(verifier: string) {
  const data = new TextEncoder().encode(verifier)
  return base64url(crypto.subtle ? await crypto.subtle.digest('SHA-256', data) : sha256(data))
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

/** 整页跳转到认证模块；silent 时带 prompt=none，SSO 会话有效则无登录页；prompt=select_tenant 用于切换租户，tenant 直接指定目标租户 */
export async function startLogin({ silent = true, returnTo = location.pathname + location.search, prompt = '', tenant = '' } = {}) {
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
  if (tenant)
    params.set('tenant', tenant)
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
