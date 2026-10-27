import os
import uuid
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from tortoise import timezone
from tortoise.expressions import F, Q

from app.core.ctx import CTX_TENANT_ID, CTX_USER_ID
from app.core.dependency import is_system_tenant
from app.domains.annotation.models import Item, Task, Template
from app.domains.annotation.schemas import ItemSave, TaskCreate, TemplateCreate, TemplateUpdate
from app.domains.users.models import User
from app.schemas import Success, SuccessExtra
from app.settings import settings
from app.utils.storage import get_minio_client

router = APIRouter()

# shortcut: 文件经后端转存 MinIO，单文件上限 50 MB；海量 / 大文件改为预签名直传与引用模式（docs/platform/annotation/integration.md）
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TEXT_SIZE = 1024 * 1024
# 上传文件按类型填入编辑器 task.data 的字段，模板用 $image / $video / $audio / $text 引用
DATA_KEYS = {"image": "image", "video": "video", "audio": "audio"}
# data 中值为该占位的字段，读取时替换为 file 的预签名地址
FILE_REF = "$file"


def _tenant_q() -> Q:
    return Q() if is_system_tenant() else Q(tenant_id=CTX_TENANT_ID.get())


async def _current_user() -> User:
    return await User.get(id=CTX_USER_ID.get())


# ---- 场景模板 ----


@router.get("/template/list", summary="查看场景模板列表")
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    name: str = Query(""),
    modality: str = Query(""),
):
    q = Q() if is_system_tenant() else Q(tenant_id=CTX_TENANT_ID.get()) | Q(scope="system")
    if name:
        q &= Q(name__icontains=name) | Q(code__icontains=name)
    if modality:
        q &= Q(modality=modality)
    total = await Template.filter(q).count()
    rows = await Template.filter(q).order_by("scope", "-updated_at").offset((page - 1) * page_size).limit(page_size)
    return SuccessExtra(data=[await t.to_dict() for t in rows], total=total, page=page, page_size=page_size)


@router.get("/template/get", summary="查看场景模板")
async def get_template(id: int = Query(...)):
    q = Q() if is_system_tenant() else Q(tenant_id=CTX_TENANT_ID.get()) | Q(scope="system")
    template = await Template.filter(q, id=id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return Success(data=await template.to_dict())


@router.post("/template/create", summary="新建场景模板")
async def create_template(req: TemplateCreate):
    tenant_id = CTX_TENANT_ID.get()
    if await Template.filter(Q(code=req.code) & (Q(tenant_id=tenant_id) | Q(scope="system"))).exists():
        raise HTTPException(status_code=400, detail="模板编码已存在")
    user = await _current_user()
    template = await Template.create(
        tenant_id=tenant_id,
        scope="system" if is_system_tenant() else "tenant",
        created_by=user.sub,
        **req.model_dump(),
    )
    return Success(data=await template.to_dict())


@router.post("/template/update", summary="修改场景模板")
async def update_template(req: TemplateUpdate):
    # 系统模板只能由系统租户修改；已建工单使用建单时的快照，不受影响
    template = await Template.filter(id=req.id, tenant_id=CTX_TENANT_ID.get()).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在或无权修改")
    template.update_from_dict(req.model_dump(exclude={"id"}))
    template.version += 1
    await template.save()
    return Success(data=await template.to_dict())


# ---- 标注工单 ----


@router.get("/task/list", summary="查看标注工单列表")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    name: str = Query(""),
    status: str = Query(""),
):
    q = _tenant_q()
    if name:
        q &= Q(name__icontains=name)
    if status:
        q &= Q(status=status)
    total = await Task.filter(q).count()
    rows = await Task.filter(q).order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    return SuccessExtra(
        data=[await t.to_dict(exclude_fields=["config"]) for t in rows], total=total, page=page, page_size=page_size
    )


@router.get("/task/get", summary="查看标注工单")
async def get_task(id: int = Query(...)):
    task = await Task.filter(_tenant_q(), id=id).first()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    return Success(data=await task.to_dict())


@router.post("/task/create", summary="新建标注工单")
async def create_task(req: TaskCreate):
    tenant_id = CTX_TENANT_ID.get()
    template = await Template.filter(Q(tenant_id=tenant_id) | Q(scope="system"), id=req.template_id).first()
    if not template:
        raise HTTPException(status_code=400, detail="场景模板不存在")
    user = await _current_user()
    task = await Task.create(
        tenant_id=tenant_id,
        name=req.name,
        template_id=template.id,
        template_name=template.name,
        template_ref=f"{template.code}@{template.version}",
        config=template.config,
        created_by=user.sub,
        creator_name=user.alias or user.username,
    )
    return Success(data=await task.to_dict(exclude_fields=["config"]))


@router.post("/task/upload", summary="上传标注数据")
async def upload_item(task_id: int = Form(...), file: UploadFile = File(...)):
    task = await Task.filter(_tenant_q(), id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    media_type = file.content_type or ""
    kind = media_type.split("/")[0]
    item_key = uuid.uuid4().hex[:16]
    name = os.path.basename(file.filename or item_key)[:255]

    if kind == "text":
        content = await file.read(MAX_TEXT_SIZE + 1)
        if len(content) > MAX_TEXT_SIZE:
            raise HTTPException(status_code=413, detail="文本文件不能超过 1 MB")
        try:
            data, object_name = {"text": content.decode("utf-8")}, ""
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文本文件须为 UTF-8 编码")
    elif kind in DATA_KEYS:
        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="单个文件不能超过 50 MB")
        # 路径规则见 docs/storage.md；文件名不进路径，用条目 ID
        ext = os.path.splitext(name)[1].lower()[:10]
        object_name = f"annotation/{task.tenant_id}/kaifang-meta-console/tasks/{task.id}/files/{item_key}{ext}"
        await run_in_threadpool(
            get_minio_client().put_object,
            settings.MINIO_BUCKET,
            object_name,
            BytesIO(content),
            len(content),
            content_type=media_type,
        )
        data = {DATA_KEYS[kind]: FILE_REF}
    else:
        raise HTTPException(status_code=400, detail="仅支持图像、视频、音频与 UTF-8 文本文件")

    item = await Item.create(
        tenant_id=task.tenant_id, task_id=task.id, item_key=item_key, name=name, file=object_name, data=data
    )
    await Task.filter(id=task.id).update(item_count=F("item_count") + 1)
    await Task.filter(id=task.id).update(status="READY" if task.labeled_count == 0 else "LABELING")
    return Success(data=await item.to_dict(exclude_fields=["result"]))


# ---- 标注条目 ----


@router.get("/item/list", summary="查看标注条目列表")
async def list_items(
    task_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    status: str = Query(""),
    name: str = Query(""),
):
    q = _tenant_q() & Q(task_id=task_id)
    if status:
        q &= Q(status=status)
    if name:
        q &= Q(name__icontains=name)
    total = await Item.filter(q).count()
    rows = await Item.filter(q).order_by("id").offset((page - 1) * page_size).limit(page_size)
    return SuccessExtra(
        data=[await i.to_dict(exclude_fields=["result", "data"]) for i in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/item/get", summary="查看标注条目")
async def get_item(task_id: int = Query(...), id: int = Query(None, description="缺省时取第一个待标注条目")):
    task = await Task.filter(_tenant_q(), id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="工单不存在")
    items = Item.filter(task_id=task.id)
    if id:
        item = await items.filter(id=id).first()
    else:
        item = await items.filter(status="PENDING").order_by("id").first() or await items.order_by("id").first()
    if not item:
        raise HTTPException(status_code=404, detail="工单下还没有数据")

    data = dict(item.data)
    for key, value in data.items():
        if value == FILE_REF:
            data[key] = await run_in_threadpool(
                get_minio_client(public=True).presigned_get_object, settings.MINIO_BUCKET, item.file
            )
    prev_item = await items.filter(id__lt=item.id).order_by("-id").first()
    next_item = await items.filter(id__gt=item.id).order_by("id").first()
    return Success(
        data={
            "task": await task.to_dict(),
            "item": {**await item.to_dict(), "data": data},
            "index": await items.filter(id__lte=item.id).count(),
            "prev_id": prev_item.id if prev_item else None,
            "next_id": next_item.id if next_item else None,
        }
    )


@router.post("/item/save", summary="保存或提交标注结果")
async def save_item(req: ItemSave):
    item = await Item.filter(_tenant_q(), id=req.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    if req.draft:
        item.result = req.result
        await item.save(update_fields=["result"])
        return Success(msg="已保存")
    user = await _current_user()
    item.result = req.result
    item.status = "LABELED"
    item.annotated_by = user.sub
    item.annotator_name = user.alias or user.username
    item.annotated_at = timezone.now()
    await item.save()

    labeled = await Item.filter(task_id=item.task_id, status="LABELED").count()
    task = await Task.get(id=item.task_id)
    task.labeled_count = labeled
    task.status = "COMPLETED" if labeled >= task.item_count else "LABELING"
    await task.save()
    return Success(msg="已提交")
