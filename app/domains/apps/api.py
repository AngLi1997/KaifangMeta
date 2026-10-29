"""应用接入：控制台经认证模块接口操作，不访问 iam 表（docs/platform/auth/app-onboarding.md「应用管理」）"""

from fastapi import APIRouter, HTTPException, Query

from app.core.dependency import require_system_tenant
from app.domains.apps.schemas import AppCreate, AppRef, AppSecret, AppStatus, AppUpdate
from app.iam import apps
from app.iam.service import AccountError
from app.schemas.base import Success

router = APIRouter()


@router.get("/list", summary="查看接入应用")
async def list_apps(keyword: str = Query("", description="名称或 client_id")):
    require_system_tenant()
    return Success(data=await apps.list_apps(keyword.strip()))


@router.get("/get", summary="查看接入应用详情")
async def get_app(client_id: str = Query(...)):
    require_system_tenant()
    app = await apps.get_app(client_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    return Success(data=app)


@router.post("/create", summary="注册应用")
async def create_app(req: AppCreate):
    require_system_tenant()
    try:
        app, once = await apps.create_app({"client_id": req.client_id, **req.fields()})
    except AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data={"app": app, "secrets": once})


@router.post("/update", summary="修改应用")
async def update_app(req: AppUpdate):
    require_system_tenant()
    try:
        once = await apps.update_app(req.client_id, req.fields())
    except AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data={"secrets": once})


@router.post("/status", summary="上线或停用应用")
async def set_status(req: AppStatus):
    require_system_tenant()
    try:
        await apps.set_status(req.client_id, req.status)
    except AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(msg="已上线" if req.status == "online" else "已停用")


@router.post("/sync", summary="下发应用网关配置")
async def sync(req: AppRef):
    require_system_tenant()
    try:
        await apps.sync(req.client_id)
    except AccountError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return Success(msg="已下发")


@router.post("/secret/rotate", summary="轮换应用密钥")
async def rotate_secret(req: AppSecret):
    require_system_tenant()
    try:
        once = await apps.rotate_secret(req.client_id, req.kind)
    except AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data={"secrets": once})
