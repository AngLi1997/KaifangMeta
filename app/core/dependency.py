import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request
from tortoise.transactions import in_transaction

from app.core.ctx import CTX_TENANT_ID, CTX_USER_ID
from app.domains.authorization.models import Api, Role
from app.domains.users.models import User
from app.settings import settings

# 网关签名时间窗（docs/gateway.md「身份头与网关签名」）
SIGN_WINDOW_MS = 60_000


@dataclass
class KmContext:
    user: str  # 用户 sub，Service Token 时为调用方 client_id
    tenant: str
    client: str
    principal_type: str  # user | service
    on_behalf_of: str  # 模式 A 代表用户：被代表用户的 sub，网关仅在调用方有 delegate:user 时保留


def verify_gateway_identity(request: Request, secret: str) -> KmContext:
    """校验网关注入的 X-KM-* 身份头与签名；签名串 = method + path（含 ?query）+ ts + user + tenant + client + on_behalf_of"""
    h = request.headers
    ctx = KmContext(
        user=h.get("x-km-user-id", ""),
        tenant=h.get("x-km-tenant-id", ""),
        client=h.get("x-km-client-id", ""),
        principal_type=h.get("x-km-principal-type", ""),
        on_behalf_of=h.get("x-km-on-behalf-of", ""),
    )
    ts, sign = h.get("x-km-ts", ""), h.get("x-km-sign", "")
    if not (ctx.user and ts.isdigit() and sign):
        raise HTTPException(status_code=401, detail="缺少网关身份头")
    if abs(time.time() * 1000 - int(ts)) > SIGN_WINDOW_MS:
        raise HTTPException(status_code=401, detail="网关签名已过期")
    query = request.scope.get("query_string", b"").decode("latin-1")
    path = f"{request.url.path}?{query}" if query else request.url.path
    message = f"{request.method}{path}{ts}{ctx.user}{ctx.tenant}{ctx.client}{ctx.on_behalf_of}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sign):
        raise HTTPException(status_code=401, detail="网关签名无效")
    return ctx


class AuthControl:
    """平台控制台（模式 A）：只信任网关签名的身份头，按 sub 关联本地用户"""

    @classmethod
    async def identify(cls, request: Request) -> Optional["User"]:
        ctx = verify_gateway_identity(request, settings.CONSOLE_GATEWAY_SECRET)
        CTX_TENANT_ID.set(ctx.tenant)
        if ctx.principal_type != "user":
            raise HTTPException(status_code=403, detail="控制台只接受用户身份")
        user = await User.filter(sub=ctx.user).first()
        # 身份有效但未开通控制台：权限问题，返回 403（docs/auth-flow.md 失败语义）
        if not user:
            raise HTTPException(status_code=403, detail="该账号未开通平台控制台")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="控制台用户已被禁用")
        return user

    @classmethod
    async def is_authed(cls, request: Request):
        user = await cls.identify(request)
        CTX_USER_ID.set(user.id)
        # 整个请求在事务内执行并 SET LOCAL app.tenant_id，供 RLS 兜底（docs/gateway.md「轻租户」）
        async with in_transaction("default") as console_conn, in_transaction("iam") as iam_conn:
            for conn in (console_conn, iam_conn):
                await conn.execute_query(
                    "SELECT set_config('app.tenant_id', $1, true), set_config('app.sub', $2, true)",
                    [CTX_TENANT_ID.get(), user.sub],
                )
            yield user


def is_system_tenant() -> bool:
    """系统租户持有 system 范围，可跨租户；其他租户的请求只能访问本租户数据"""
    return CTX_TENANT_ID.get() == settings.IAM_SYSTEM_TENANT


def require_system_tenant() -> None:
    if not is_system_tenant():
        raise HTTPException(status_code=403, detail="跨租户操作仅限系统租户")


async def tenant_roles(user: User) -> list[Role]:
    """当前 Token 租户内生效的角色：system 范围的角色只在系统租户生效"""
    roles = await Role.filter(bindings__user_id=user.id, bindings__tenant_id=CTX_TENANT_ID.get()).distinct()
    return [role for role in roles if role.scope == "tenant" or is_system_tenant()]


def is_platform_superuser(user: User) -> bool:
    return user.is_superuser and is_system_tenant()


async def user_apis(user: User) -> list[Api]:
    if is_platform_superuser(user):
        return await Api.all()
    return await Api.filter(role_apis__id__in=[role.id for role in await tenant_roles(user)]).distinct()


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if is_platform_superuser(current_user):
            return
        method = request.method
        path = request.url.path
        if not await tenant_roles(current_user):
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        if (method, path) not in {(api.method, api.path) for api in await user_apis(current_user)}:
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
