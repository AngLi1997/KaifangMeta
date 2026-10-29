"""身份账号管理：控制台经认证模块接口操作，不访问 iam 表"""

from fastapi import APIRouter, HTTPException, Query

from app.core.ctx import CTX_TENANT_ID
from app.core.dependency import is_system_tenant
from app.iam import service as iam
from app.domains.accounts.schemas import AccountCreate, AccountUpdate
from app.domains.users.models import User
from app.schemas.base import Success, SuccessExtra

router = APIRouter()


@router.get("/list", summary="查看身份账号列表")
async def list_accounts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=500, description="每页数量"),
    username: str = Query("", description="登录名"),
    tenant_id: str = Query("", description="租户"),
    status: str = Query("", description="账号状态"),
    org_id: int | None = Query(None, description="所属机构"),
):
    if not is_system_tenant():
        tenant_id = CTX_TENANT_ID.get()
    total, data = await iam.list_accounts(
        page=page, page_size=page_size, username=username, tenant_id=tenant_id, status=status, org_id=org_id
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/create", summary="新建身份账号")
async def create_account(req: AccountCreate):
    if not is_system_tenant() and (req.tenant_id != CTX_TENANT_ID.get() or req.member_tenant_ids):
        raise HTTPException(status_code=403, detail="只能在本租户内新建账号")
    try:
        account = await iam.create_account(
            req.tenant_id,
            req.username,
            str(req.email) if req.email else None,
            req.password,
            req.member_tenant_ids,
            req.name,
            req.phone,
            req.org_id,
        )
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data=account)


@router.post("/update", summary="修改身份账号")
async def update_account(req: AccountUpdate):
    account = await iam.get_account(req.sub)
    if not account:
        raise HTTPException(status_code=404, detail="身份账号不存在")
    member_tenant_ids = req.member_tenant_ids
    if not is_system_tenant():
        # 租户管理员只管主租户在本租户的账号，不能转移租户或调整跨租户成员
        if account["tenant_id"] != CTX_TENANT_ID.get() or req.tenant_id != account["tenant_id"]:
            raise HTTPException(status_code=403, detail="只能修改本租户的账号")
        member_tenant_ids = None
    is_console_admin = await User.filter(sub=req.sub, is_superuser=True).exists()
    if is_console_admin and (req.status != "active" or req.tenant_id != account["tenant_id"]):
        raise HTTPException(status_code=400, detail="控制台超级管理员不能停用或转移租户")
    try:
        await iam.update_account(
            req.sub,
            req.tenant_id,
            req.username,
            str(req.email) if req.email else None,
            req.status,
            req.password,
            member_tenant_ids,
            req.name,
            req.phone,
            req.org_id,
        )
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(msg="身份账号已更新")


@router.delete("/delete", summary="删除身份账号")
async def delete_account(sub: str = Query(..., description="身份账号 sub")):
    account = await iam.get_account(sub)
    if not account:
        raise HTTPException(status_code=404, detail="身份账号不存在")
    if not is_system_tenant() and account["tenant_id"] != CTX_TENANT_ID.get():
        raise HTTPException(status_code=403, detail="只能删除本租户的账号")
    if await User.filter(sub=sub, is_superuser=True).exists():
        raise HTTPException(status_code=400, detail="控制台超级管理员不能删除")
    try:
        await iam.delete_account(sub)
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 控制台成员随身份账号删除，角色绑定级联删除
    await User.filter(sub=sub).delete()
    return Success(msg="身份账号已删除")
