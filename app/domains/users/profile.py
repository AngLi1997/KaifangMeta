from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.domains.authorization.models import Api, Menu
from app.core.ctx import CTX_TENANT_ID, CTX_USER_ID
from app.core.dependency import DependAuth, is_platform_superuser, tenant_roles, user_apis
from app.domains.users.controller import user_controller
from app.domains.users.models import User
from app.domains.users.schemas import UpdatePassword
from app.iam import service as iam
from app.schemas.base import Fail, Success
from app.settings import settings
from app.utils.storage import get_minio_client

router = APIRouter()
MAX_AVATAR_SIZE = 2 * 1024 * 1024


@router.get("/userinfo", summary="查看用户信息", dependencies=[DependAuth])
async def get_userinfo():
    user_id = CTX_USER_ID.get()
    # 登录发生在认证模块，控制台以每次加载用户信息作为最近访问时间
    await user_controller.update_last_login(user_id)
    user_obj = await user_controller.get(id=user_id)
    data = await user_obj.to_dict()
    # 当前租户与可切换的租户；切换租户 = 带 prompt=select_tenant 重新授权
    tenant_id = CTX_TENANT_ID.get()
    data["tenant_id"] = tenant_id
    # 姓名、电话以身份账号为准
    account = await iam.get_account(user_obj.sub) or {}
    data["alias"], data["phone"] = account.get("name"), account.get("phone")
    data["is_system_tenant"] = tenant_id == settings.IAM_SYSTEM_TENANT
    data["tenants"] = [
        {"id": tid, "name": name} for tid, name in await iam.tenant_names(await iam.account_tenants(user_obj.sub))
    ]
    if user_obj.avatar:
        data["avatar"] = await run_in_threadpool(
            get_minio_client(public=True).presigned_get_object,
            settings.MINIO_BUCKET,
            user_obj.avatar,
        )
    return Success(data=data)


@router.post("/avatar", summary="上传用户头像", dependencies=[DependAuth])
async def upload_avatar(file: UploadFile = File(...)):
    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="头像不能超过 2 MB")

    media_type = file.content_type
    valid_image = (
        media_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
        or media_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
        or media_type == "image/webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    )
    if not valid_image:
        raise HTTPException(status_code=400, detail="仅支持 JPEG、PNG 或 WebP 图片")

    tenant_id = CTX_TENANT_ID.get()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="缺少租户信息")
    user = await user_controller.get(id=CTX_USER_ID.get())
    # 路径规则见 docs/storage.md；旧头像的完整对象名存在 user.avatar，仍可读取
    object_name = f"console/{tenant_id}/avatars/{user.sub}"
    client = get_minio_client()
    await run_in_threadpool(
        client.put_object,
        settings.MINIO_BUCKET,
        object_name,
        BytesIO(content),
        len(content),
        content_type=media_type,
    )
    user.avatar = object_name
    await user.save()
    avatar = await run_in_threadpool(
        get_minio_client(public=True).presigned_get_object, settings.MINIO_BUCKET, object_name
    )
    return Success(msg="头像已更新", data={"avatar": avatar})


@router.get("/usermenu", summary="查看用户菜单", dependencies=[DependAuth])
async def get_user_menu():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    if is_platform_superuser(user_obj):
        menus: list[Menu] = await Menu.all()
    else:
        roles = await tenant_roles(user_obj)
        menus = await Menu.filter(role_menus__id__in=[role.id for role in roles]).distinct()
    parent_menus: list[Menu] = []
    for menu in menus:
        if menu.parent_id == 0:
            parent_menus.append(menu)
    res = []
    for parent_menu in parent_menus:
        parent_menu_dict = await parent_menu.to_dict()
        parent_menu_dict["children"] = []
        for menu in menus:
            if menu.parent_id == parent_menu.id:
                parent_menu_dict["children"].append(await menu.to_dict())
        res.append(parent_menu_dict)
    return Success(data=res)


def _perm_code(api: Api) -> str:
    # 前端权限码沿用 method + /api/v1/...，去掉网关前缀
    return api.method.lower() + api.path.removeprefix(settings.CONSOLE_GATEWAY_PREFIX)


@router.get("/userapi", summary="查看用户API", dependencies=[DependAuth])
async def get_user_api():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    return Success(data=[_perm_code(api) for api in await user_apis(user_obj)])


@router.post("/update_password", summary="修改密码", dependencies=[DependAuth])
async def update_user_password(req_in: UpdatePassword):
    user = await user_controller.get(CTX_USER_ID.get())
    try:
        await iam.change_password(user.sub, req_in.old_password, req_in.new_password)
    except iam.AccountError as e:
        return Fail(msg=str(e))
    return Success(msg="修改成功")
