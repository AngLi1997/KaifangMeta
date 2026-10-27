"""SSO 会话、授权码、Refresh Token 与吊销，全部存 Redis（平台实例无状态）"""

import base64
import hashlib
import json
import secrets
import time

from app.core.redis import redis
from app.settings import settings

from . import keys

SSO = "km:iam:sso:"  # sid -> {sub, tid}
SUB_SIDS = "km:iam:sub_sids:"  # sub -> {sid}
CODE = "km:iam:code:"  # code -> 授权请求上下文
RT = "km:iam:rt:"  # sha256(refresh_token) -> {sub, tid, sid, client_id}
RT_USED = "km:iam:rt_used:"  # 已轮换的 refresh token，再次出现视为泄露
SID_RTS = "km:iam:sid_rts:"  # sid -> {sha256(refresh_token)}
# 与网关插件 km-identity 约定的吊销键
REVOKE_SID = "km:revoke:sid:"
REVOKE_SUB = "km:revoke:sub:"
REVOKE_TENANT = "km:revoke:tenant:"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_sso_session(sub: str, tid: str) -> str:
    sid = "s_" + secrets.token_hex(12)
    ttl = settings.IAM_SSO_SESSION_TTL
    await redis.set(SSO + sid, json.dumps({"sub": sub, "tid": tid}), ex=ttl)
    await redis.sadd(SUB_SIDS + sub, sid)
    await redis.expire(SUB_SIDS + sub, ttl)
    return sid


async def set_sso_tenant(sid: str, tid: str) -> None:
    """记住会话最近选择的租户，下次授权默认沿用；已签发的 Token 各自保留自己的 tid"""
    ttl = await redis.ttl(SSO + sid)
    session = await get_sso_session(sid)
    if session and ttl > 0:
        await redis.set(SSO + sid, json.dumps(session | {"tid": tid}), ex=ttl)


async def get_sso_session(sid: str | None) -> dict | None:
    if not sid:
        return None
    raw = await redis.get(SSO + sid)
    return json.loads(raw) if raw else None


async def issue_code(ctx: dict) -> str:
    code = secrets.token_urlsafe(32)
    await redis.set(CODE + code, json.dumps(ctx), ex=60)
    return code


async def consume_code(code: str) -> dict | None:
    raw = await redis.getdel(CODE + code)
    return json.loads(raw) if raw else None


def verify_pkce(verifier: str, challenge: str) -> bool:
    digest = hashlib.sha256(verifier.encode()).digest()
    return secrets.compare_digest(base64.urlsafe_b64encode(digest).rstrip(b"=").decode(), challenge)


async def issue_tokens(sub: str, tid: str, sid: str, client_id: str) -> dict:
    now = int(time.time())
    access_token = await keys.sign(
        {
            "iss": settings.IAM_ISSUER,
            "sub": sub,
            "tid": tid,
            "aud": [client_id],
            "azp": client_id,
            "sid": sid,
            "scope": "openid profile",
            "iat": now,
            "exp": now + settings.IAM_ACCESS_TOKEN_TTL,
            "jti": secrets.token_hex(8),
        }
    )
    refresh_token = secrets.token_urlsafe(48)
    rt_hash = _hash(refresh_token)
    ttl = settings.IAM_REFRESH_TOKEN_TTL
    await redis.set(RT + rt_hash, json.dumps({"sub": sub, "tid": tid, "sid": sid, "client_id": client_id}), ex=ttl)
    await redis.sadd(SID_RTS + sid, rt_hash)
    await redis.expire(SID_RTS + sid, ttl)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.IAM_ACCESS_TOKEN_TTL,
        "refresh_token": refresh_token,
        "scope": "openid profile",
    }


async def issue_service_token(client_id: str, tid: str, scopes: list[str]) -> dict:
    """client credentials：sub = client_id，aud = 平台（docs/gateway.md「服务间调用」）"""
    now = int(time.time())
    scope = " ".join(scopes)
    access_token = await keys.sign(
        {
            "iss": settings.IAM_ISSUER,
            "sub": client_id,
            "tid": tid,
            "aud": [settings.PLATFORM_CLIENT_ID],
            "azp": client_id,
            "km_principal": "service",
            "scope": scope,
            "iat": now,
            "exp": now + settings.IAM_SERVICE_TOKEN_TTL,
            "jti": secrets.token_hex(8),
        }
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.IAM_SERVICE_TOKEN_TTL,
        "scope": scope,
    }


async def issue_exchanged_token(subject: dict, actor_client: str, audience: str, scopes: list[str]) -> dict:
    """Token Exchange（RFC 8693）：保留用户 sub / sid，act 记录调用方；有效期不超过原用户 Token"""
    now = int(time.time())
    exp = min(subject["exp"], now + settings.IAM_ACCESS_TOKEN_TTL)
    scope = " ".join(scopes)
    access_token = await keys.sign(
        {
            "iss": settings.IAM_ISSUER,
            "sub": subject["sub"],
            "tid": subject["tid"],
            "sid": subject.get("sid"),
            "aud": [audience],
            "azp": actor_client,
            "act": {"sub": actor_client},
            "scope": scope,
            "iat": now,
            "exp": exp,
            "jti": secrets.token_hex(8),
        }
    )
    return {
        "access_token": access_token,
        "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "token_type": "Bearer",
        "expires_in": exp - now,
        "scope": scope,
    }


async def is_revoked(sid: str | None, sub: str) -> bool:
    keys_ = [REVOKE_SUB + sub] + ([REVOKE_SID + sid] if sid else [])
    return await redis.exists(*keys_) > 0


async def rotate_refresh_token(refresh_token: str, client_id: str) -> dict | None:
    """一次一用、每次轮换；旧串再次出现则吊销整个 sid（docs/auth-flow.md「Token 续期」）"""
    rt_hash = _hash(refresh_token)
    raw = await redis.getdel(RT + rt_hash)
    if not raw:
        used_sid = await redis.get(RT_USED + rt_hash)
        if used_sid:
            await revoke_sid(used_sid)
        return None
    ctx = json.loads(raw)
    if ctx["client_id"] != client_id or not await get_sso_session(ctx["sid"]):
        return None
    await redis.set(RT_USED + rt_hash, ctx["sid"], ex=settings.IAM_REFRESH_TOKEN_TTL)
    await redis.srem(SID_RTS + ctx["sid"], rt_hash)
    return ctx


async def revoke_sid(sid: str) -> None:
    """吊销会话：网关下一次请求即拒绝（TTL = Access Token 最长剩余有效期）"""
    await redis.set(REVOKE_SID + sid, 1, ex=settings.IAM_ACCESS_TOKEN_TTL)
    session = await get_sso_session(sid)
    if session:
        await redis.srem(SUB_SIDS + session["sub"], sid)
    rt_hashes = await redis.smembers(SID_RTS + sid)
    await redis.delete(SSO + sid, SID_RTS + sid, *[RT + h for h in rt_hashes])


async def revoke_sub(sub: str) -> None:
    """禁用账号：吊销 sub 及其全部会话"""
    await redis.set(REVOKE_SUB + sub, 1, ex=settings.IAM_ACCESS_TOKEN_TTL)
    for sid in await redis.smembers(SUB_SIDS + sub):
        await revoke_sid(sid)
    await redis.delete(SUB_SIDS + sub)


async def set_tenant_revoked(tenant_id: str, revoked: bool) -> None:
    key = REVOKE_TENANT + tenant_id
    if revoked:
        ttl = max(settings.IAM_ACCESS_TOKEN_TTL, settings.IAM_SERVICE_TOKEN_TTL)
        await redis.set(key, 1, ex=ttl)
    else:
        # shortcut: 重新启用会恢复未过期令牌；要强制重新登录时升级为按 iat 截断租户令牌。
        await redis.delete(key)
