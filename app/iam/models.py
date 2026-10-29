from tortoise import fields, models


class Tenant(models.Model):
    id = fields.CharField(max_length=32, pk=True)
    name = fields.CharField(max_length=64)
    status = fields.CharField(max_length=16, default="active")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tenant"


class Account(models.Model):
    """身份账号：登录名、凭据、全局唯一且不复用的 sub、启停状态"""

    sub = fields.CharField(max_length=32, pk=True)
    tenant_id = fields.CharField(max_length=32, index=True)
    username = fields.CharField(max_length=64, unique=True)
    email = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=64, null=True)
    phone = fields.CharField(max_length=20, null=True)
    # 所属机构，须属于主租户（docs/platform/auth/identity.md「机构」）
    org_id = fields.BigIntField(null=True, index=True)
    password_hash = fields.CharField(max_length=255)
    status = fields.CharField(max_length=16, default="active", index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "account"


class Org(models.Model):
    """机构：按租户维护的机构树，层级按 parent_id 计算；id 可在导入时指定以保留存量系统的机构 ID"""

    id = fields.BigIntField(pk=True)
    tenant_id = fields.CharField(max_length=32, index=True)
    parent_id = fields.BigIntField(null=True, index=True)
    code = fields.CharField(max_length=64)
    name = fields.CharField(max_length=128)
    sort_order = fields.IntField(default=0)
    status = fields.CharField(max_length=16, default="active")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "org"
        unique_together = (("tenant_id", "code"),)


class TenantMember(models.Model):
    """跨租户成员：账号在主租户之外还可登录的租户，一个 Token 仍只含一个 tid"""

    id = fields.BigIntField(pk=True)
    sub = fields.CharField(max_length=32)
    tenant_id = fields.CharField(max_length=32, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tenant_member"
        unique_together = (("sub", "tenant_id"),)


class Client(models.Model):
    """接入应用（OIDC client），控制台为内置应用 kaifang-meta-console（docs/platform/auth/app-onboarding.md）"""

    client_id = fields.CharField(max_length=64, pk=True)
    name = fields.CharField(max_length=64)
    type = fields.CharField(max_length=16, default="web")
    redirect_uris = fields.JSONField(default=list)
    post_logout_redirect_uris = fields.JSONField(default=list)
    grant_types = fields.JSONField(default=list)
    # 机密客户端才有：只存哈希，明文仅在注册时显示一次
    client_secret_hash = fields.CharField(max_length=255, null=True)
    # platform_access.scopes：Service Token 可获得的平台 scope
    scopes = fields.JSONField(default=list)
    tenants = fields.JSONField(default=list)
    # 事件订阅：分发器需要明文 event_secret 计算签名
    event_endpoint = fields.CharField(max_length=255, null=True)
    event_secret = fields.CharField(max_length=128, null=True)
    event_subscribe = fields.JSONField(default=list)
    # 门户磁贴：icon、entry、description、order；无 entry 不在门户显示（docs/platform/auth/portal.md）
    portal = fields.JSONField(default=dict)
    # 网关：prefix、routes[{path, nodes, health}]、public_paths、rate_limit；平台经 APISIX Admin API 下发
    gateway = fields.JSONField(default=dict)
    # 网关签名身份头的 HMAC 密钥（明文，网关与业务后端共用），不进日志、列表与导出
    gateway_secret = fields.CharField(max_length=128, null=True)
    owner = fields.CharField(max_length=64, null=True)
    # online：已上线；disabled：已停用（网关返回 503，授权页拒绝）
    status = fields.CharField(max_length=16, default="online")
    # 网关下发状态：synced / pending；未配置网关路由时为空
    sync_status = fields.CharField(max_length=16, null=True)
    synced_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "client"


class SigningKey(models.Model):
    """Token 签名密钥，kid 轮换时新旧并存，JWKS 公布全部未退役公钥"""

    kid = fields.CharField(max_length=32, pk=True)
    private_pem = fields.TextField()
    public_jwk = fields.JSONField()
    active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "signing_key"


class Outbox(models.Model):
    """事件 outbox：与账号变更同一事务写入，由事件分发器投递（docs/communication.md「事件投递」）"""

    id = fields.BigIntField(pk=True)
    type = fields.CharField(max_length=64)
    subject = fields.CharField(max_length=64)
    tenant_id = fields.CharField(max_length=32)
    data = fields.JSONField()
    dispatched = fields.BooleanField(default=False, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "outbox"


class Delivery(models.Model):
    """按订阅展开的投递记录，每个应用独立重试，超限标记 dead"""

    id = fields.BigIntField(pk=True)
    outbox_id = fields.BigIntField(index=True)
    client_id = fields.CharField(max_length=64, index=True)
    status = fields.CharField(max_length=16, default="pending", index=True)
    attempts = fields.IntField(default=0)
    next_attempt_at = fields.DatetimeField(index=True)
    last_error = fields.CharField(max_length=500, null=True)
    delivered_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "delivery"
        unique_together = (("outbox_id", "client_id"),)
