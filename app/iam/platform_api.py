"""平台 API：身份目录，经网关 /kaifang-meta/platform/iam/v1/*（模式 A，scope = directory:read）

只返回身份账号基础字段与当前租户机构，不含角色或权限（docs/platform/auth/identity.md）。
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.dependency import KmContext, verify_gateway_identity
from app.settings import settings

from . import service

router = APIRouter(prefix="/kaifang-meta/platform/iam/v1", tags=["身份目录"])


async def platform_context(request: Request) -> KmContext:
    ctx = verify_gateway_identity(request, settings.PLATFORM_GATEWAY_SECRET)
    if not await service.tenant_is_active(ctx.tenant):
        raise HTTPException(status_code=403, detail="租户已停用")
    if ctx.on_behalf_of:
        # 代表用户：平台校验该 sub 在当前租户有效；权限仍以调用方应用为准，用户只用于审计与数据过滤
        if not await service.account_in_tenant(ctx.on_behalf_of, ctx.tenant):
            raise HTTPException(status_code=403, detail="被代表用户在当前租户无效")
    return ctx


def _audit(ctx: KmContext) -> dict:
    return {"caller": ctx.client, "principal_type": ctx.principal_type, "on_behalf_of": ctx.on_behalf_of or None}


@router.get("/accounts/{sub}", summary="按 sub 查询身份账号")
async def get_account(sub: str, ctx: KmContext = Depends(platform_context)):
    account = await service.get_account(sub)
    # 租户是隔离边界：只能查本租户账号（主租户或成员）
    if not account or not await service.account_belongs(sub, ctx.tenant):
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"data": account, "audit": _audit(ctx)}


@router.get("/accounts", summary="按登录名查询身份账号")
async def find_account(username: str, ctx: KmContext = Depends(platform_context)):
    account = await service.get_account_by_username(username)
    if not account or not await service.account_belongs(account["sub"], ctx.tenant):
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"data": account, "audit": _audit(ctx)}


@router.get("/orgs", summary="当前租户机构列表")
async def list_orgs(ctx: KmContext = Depends(platform_context)):
    return {"data": await service.list_orgs(ctx.tenant), "audit": _audit(ctx)}
