"""机构管理：控制台经认证模块接口操作，不访问 iam 表"""

from fastapi import APIRouter, HTTPException, Query

from app.core.ctx import CTX_TENANT_ID
from app.core.dependency import is_system_tenant
from app.domains.orgs.schemas import OrgCreate, OrgImport, OrgUpdate
from app.iam import service as iam
from app.schemas.base import Success

router = APIRouter()


def _tenant(tenant_id: str) -> str:
    """系统租户可指定租户，租户管理员只维护本租户"""
    return tenant_id if tenant_id and is_system_tenant() else CTX_TENANT_ID.get()


@router.get("/tree", summary="查看机构树")
async def org_tree(tenant_id: str = Query("", description="租户，仅系统租户可指定")):
    return Success(data=await iam.org_tree(_tenant(tenant_id)))


@router.post("/create", summary="新增机构")
async def create_org(req: OrgCreate):
    try:
        org = await iam.create_org(_tenant(req.tenant_id), req.parent_id, req.code, req.name, req.sort_order)
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data=org)


@router.post("/update", summary="修改机构")
async def update_org(req: OrgUpdate):
    try:
        await iam.update_org(
            _tenant(req.tenant_id), req.id, req.parent_id, req.code, req.name, req.sort_order, req.status
        )
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(msg="机构已更新")


@router.delete("/delete", summary="删除机构")
async def delete_org(id: int = Query(..., description="机构ID"), tenant_id: str = Query("")):
    try:
        await iam.delete_org(_tenant(tenant_id), id)
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(msg="机构已删除")


@router.post("/import", summary="导入机构")
async def import_orgs(req: OrgImport):
    try:
        count = await iam.import_orgs(_tenant(req.tenant_id), [row.model_dump() for row in req.orgs])
    except iam.AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Success(data={"count": count}, msg=f"已导入 {count} 个机构")
