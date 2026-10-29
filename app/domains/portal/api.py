from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.core.dependency import DependGatewayUser, KmContext
from app.domains.users.models import User
from app.iam import service as iam
from app.schemas.base import Success
from app.settings import settings
from app.utils.storage import presigned_url

router = APIRouter()


@router.get("/apps", summary="门户：我的应用")
async def my_apps(ctx: KmContext = DependGatewayUser):
    account = await iam.get_account(ctx.user) or {}
    apps = await iam.accessible_apps(ctx.user, ctx.tenant)
    member = await User.filter(sub=ctx.user, is_active=True).first()
    # 控制台磁贴只对已开通的控制台成员显示；头像存于控制台成员资料
    if not member:
        apps = [a for a in apps if a["client_id"] != settings.CONSOLE_CLIENT_ID]
    avatar = await run_in_threadpool(presigned_url, member.avatar) if member and member.avatar else None
    tenants = await iam.tenant_names(await iam.account_tenants(ctx.user))
    return Success(
        data={
            "user": {"username": account.get("username"), "name": account.get("name"), "avatar": avatar},
            "tenant_id": ctx.tenant,
            "tenants": [{"id": tid, "name": name} for tid, name in tenants],
            "apps": apps,
        }
    )
