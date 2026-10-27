from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.ctx import CTX_TENANT_ID
from app.core.dependency import is_system_tenant
from app.domains.authorization.models import Role
from app.domains.users.models import RoleBinding, User
from app.iam import service as iam
from app.schemas.base import Success, SuccessExtra
from app.settings import settings

router = APIRouter()
TENANT_ADMIN = "租户管理员"


class MemberRoles(BaseModel):
    sub: str = Field(min_length=1, max_length=32)
    tenant_id: str = Field(min_length=1, max_length=32)
    role_ids: list[int] = []


@router.get("/list", summary="读取身份账号对应的控制台授权信息")
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    query = User.all() if is_system_tenant() else User.filter(bindings__tenant_id=CTX_TENANT_ID.get()).distinct()
    total = await query.count()
    users = await query.order_by("id").offset((page - 1) * page_size).limit(page_size)
    # 非系统租户的查询经 RLS 只能看到本租户的绑定
    bindings = await RoleBinding.filter(user_id__in=[u.id for u in users]).prefetch_related("role")
    data = [
        {
            "sub": obj.sub,
            "roles": [
                {"id": b.role.id, "name": b.role.name, "tenant_id": b.tenant_id} for b in bindings if b.user_id == obj.id
            ],
            "is_superuser": obj.is_superuser,
            "is_active": obj.is_active,
            "last_login": obj.last_login.strftime(settings.DATETIME_FORMAT) if obj.last_login else None,
        }
        for obj in users
    ]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/roles", summary="设置控制台角色")
async def set_member_roles(req: MemberRoles):
    """设置账号在某租户内的控制台角色；首次授予时开通控制台成员"""
    if not is_system_tenant() and req.tenant_id != CTX_TENANT_ID.get():
        raise HTTPException(status_code=403, detail="只能设置本租户的角色")
    account = await iam.get_account(req.sub)
    if not account or not await iam.account_belongs(req.sub, req.tenant_id):
        raise HTTPException(status_code=404, detail="账号不属于该租户")
    roles = await Role.filter(id__in=req.role_ids)
    if len(roles) != len(set(req.role_ids)):
        raise HTTPException(status_code=400, detail="角色不存在")
    in_system = req.tenant_id == settings.IAM_SYSTEM_TENANT
    if any((role.scope == "system") != in_system for role in roles):
        raise HTTPException(status_code=400, detail="系统角色只能在系统租户授予，租户角色只能在业务租户授予")
    # 内置管理角色须由上级授予（docs/platform/auth/authz.md「防越权」）
    if not is_system_tenant() and any(role.name == TENANT_ADMIN for role in roles):
        raise HTTPException(status_code=403, detail="租户管理员角色只能由平台超级管理员授予")

    user = await User.get_or_none(sub=req.sub)
    if not user:
        if not roles:
            return Success(msg="未开通控制台")
        user = await User.create(sub=req.sub, username=account["username"], email=account["email"])
    current = RoleBinding.filter(user_id=user.id, tenant_id=req.tenant_id)
    if not is_system_tenant() and await current.filter(role__name=TENANT_ADMIN).exists():
        if TENANT_ADMIN not in {role.name for role in roles}:
            raise HTTPException(status_code=403, detail="租户管理员角色只能由平台超级管理员移除")
    await current.delete()
    for role in roles:
        await RoleBinding.create(user_id=user.id, role_id=role.id, tenant_id=req.tenant_id)
    return Success(msg="控制台角色已更新")
