import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.ctx import CTX_TENANT_ID
from app.core.dependency import is_system_tenant, require_system_tenant
from app.domains.tenants.schemas import TenantCreate, TenantUpdate
from app.domains.users.models import RoleBinding, User
from app.iam import service as iam
from app.iam.gateway import sync_platform_routes
from app.schemas.base import Success, SuccessExtra

router = APIRouter()


@router.get("/list", summary="查看租户列表")
async def list_tenants(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=500, description="每页数量"),
    name: str = Query("", description="租户名称"),
):
    ids = None if is_system_tenant() else [CTX_TENANT_ID.get()]
    total, data = await iam.list_tenants(page=page, page_size=page_size, name=name, ids=ids)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/create", summary="新建租户")
async def create_tenant(req: TenantCreate):
    require_system_tenant()
    tenant = await iam.create_tenant(req.name)
    # 控制台路由的开通租户列表随之更新；下发失败时整个请求事务回滚，租户不落库
    try:
        await sync_platform_routes()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"网关路由下发失败，租户未创建：{e!r}")
    return Success(data=tenant)


@router.post("/update", summary="修改租户")
async def update_tenant(req: TenantUpdate):
    require_system_tenant()
    admins = await User.filter(is_superuser=True, is_active=True).values_list("sub", flat=True)
    for sub in admins:
        account = await iam.get_account(sub)
        if account and account["status"] == "active" and account["tenant_id"] == req.id and req.status == "disabled":
            raise HTTPException(status_code=400, detail="租户中仍有控制台超级管理员，不能停用")
    try:
        await iam.update_tenant(req.id, req.name, req.status)
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(msg="租户已更新")


@router.delete("/delete", summary="删除租户")
async def delete_tenant(tenant_id: str = Query(..., description="租户ID")):
    require_system_tenant()
    try:
        await iam.delete_tenant(tenant_id)
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await RoleBinding.filter(tenant_id=tenant_id).delete()
    try:
        await sync_platform_routes()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"租户已删除，但网关路由下发失败：{e!r}")
    return Success(msg="租户已删除")
