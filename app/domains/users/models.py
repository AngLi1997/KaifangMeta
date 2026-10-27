from tortoise import fields

from app.models.base import BaseModel, TimestampMixin


class User(BaseModel, TimestampMixin):
    """控制台成员：按 sub 关联认证模块的身份账号。"""

    sub = fields.CharField(max_length=32, unique=True, description="身份账号 sub", index=True)
    username = fields.CharField(max_length=64, unique=True, description="用户名称", index=True)
    alias = fields.CharField(max_length=30, null=True, description="姓名", index=True)
    email = fields.CharField(max_length=255, null=True, unique=True, description="邮箱", index=True)
    phone = fields.CharField(max_length=20, null=True, description="电话", index=True)
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员", index=True)
    last_login = fields.DatetimeField(null=True, description="最后登录时间", index=True)
    avatar = fields.CharField(max_length=255, null=True, description="头像对象键")

    class Meta:
        table = "user"


class RoleBinding(BaseModel):
    """角色绑定：成员 × 角色 × 租户，只在 Token 的租户内生效（docs/platform/auth/authz.md「作用范围」）"""

    user = fields.ForeignKeyField("models.User", related_name="bindings")
    role = fields.ForeignKeyField("models.Role", related_name="bindings")
    tenant_id = fields.CharField(max_length=32, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "role_binding"
        unique_together = (("user", "role", "tenant_id"),)
