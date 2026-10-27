from tortoise import fields

from app.models.base import BaseModel, TimestampMixin


class Template(BaseModel, TimestampMixin):
    """场景模板：Label Studio 模板 XML；每次修改 version + 1，工单建单时快照 XML 与版本"""

    tenant_id = fields.CharField(max_length=32, index=True)
    scope = fields.CharField(max_length=16, default="tenant", description="system | tenant")
    code = fields.CharField(max_length=64)
    name = fields.CharField(max_length=64)
    modality = fields.CharField(max_length=16, description="image | text | document | video | audio")
    config = fields.TextField(description="Label Studio 模板 XML")
    version = fields.IntField(default=1)
    created_by = fields.CharField(max_length=32, default="")

    class Meta:
        table = "template"


class Task(BaseModel, TimestampMixin):
    tenant_id = fields.CharField(max_length=32, index=True)
    name = fields.CharField(max_length=128)
    mode = fields.CharField(max_length=16, default="assigned", description="assigned | free")
    template_id = fields.BigIntField()
    template_name = fields.CharField(max_length=64)
    template_ref = fields.CharField(max_length=80, description="code@version")
    config = fields.TextField(description="建单时的模板 XML 快照")
    status = fields.CharField(max_length=16, default="CREATED", index=True)
    item_count = fields.IntField(default=0)
    labeled_count = fields.IntField(default=0)
    created_by = fields.CharField(max_length=32, default="")
    creator_name = fields.CharField(max_length=64, default="")

    class Meta:
        table = "task"


class Item(BaseModel, TimestampMixin):
    """标注条目；result 只保存最新一次提交的 Label Studio 结果
    shortcut: 不保留提交历史与质检记录，做质检 / 返工时再拆出 annotation、review 表"""

    tenant_id = fields.CharField(max_length=32, index=True)
    task_id = fields.BigIntField(index=True)
    item_key = fields.CharField(max_length=64)
    name = fields.CharField(max_length=255, default="", description="原始文件名")
    file = fields.CharField(max_length=500, default="", description="MinIO 对象名")
    data = fields.JSONField(default=dict, description="编辑器 task.data；文件字段在读取时签发地址")
    status = fields.CharField(max_length=16, default="PENDING", index=True)
    result = fields.JSONField(null=True)
    annotated_by = fields.CharField(max_length=32, default="")
    annotator_name = fields.CharField(max_length=64, default="")
    annotated_at = fields.DatetimeField(null=True)

    class Meta:
        table = "item"
