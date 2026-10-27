"""认证模块对其他模块的接口：只暴露身份账号的基础字段，不含业务组织、角色或权限"""

import secrets

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.redis import redis
from app.settings import settings
from app.utils.password import get_password_hash, verify_password

from . import sessions
from .models import Account, Client, Outbox, Tenant, TenantMember

SYSTEM_TENANT = settings.IAM_SYSTEM_TENANT


class AccountError(Exception):
    pass


def _public(account: Account) -> dict:
    return {
        "sub": account.sub,
        "tenant_id": account.tenant_id,
        "username": account.username,
        "email": account.email,
        "name": account.name,
        "phone": account.phone,
        "status": account.status,
    }


def new_sub() -> str:
    """全局唯一、不复用的用户 ID"""
    return "u_" + secrets.token_hex(8)


async def get_account(sub: str) -> dict | None:
    account = await Account.get_or_none(sub=sub)
    return _public(account) if account else None


async def get_account_by_username(username: str) -> dict | None:
    account = await Account.get_or_none(username=username)
    return _public(account) if account else None


async def account_tenants(sub: str) -> list[str]:
    """账号可登录的启用租户：主租户在前，其后为成员租户"""
    account = await Account.get_or_none(sub=sub)
    if not account or account.status != "active":
        return []
    ids = [account.tenant_id] + await TenantMember.filter(sub=sub).order_by("id").values_list("tenant_id", flat=True)
    active = set(await Tenant.filter(id__in=ids, status="active").values_list("id", flat=True))
    return [i for i in ids if i in active]


async def account_belongs(sub: str, tenant_id: str) -> bool:
    """账号归属该租户（主租户或成员），不看账号与租户状态"""
    return (
        await Account.filter(sub=sub, tenant_id=tenant_id).exists()
        or await TenantMember.filter(sub=sub, tenant_id=tenant_id).exists()
    )


async def account_in_tenant(sub: str, tenant_id: str) -> bool:
    """账号启用、租户启用且账号归属该租户：签发与校验带 tid 的身份时使用"""
    return tenant_id in await account_tenants(sub)


async def authenticate(username: str, password: str) -> dict | None:
    account = await Account.get_or_none(username=username)
    if not account or not verify_password(password, account.password_hash):
        return None
    if account.status != "active":
        raise AccountError("账号已停用")
    if not await account_tenants(account.sub):
        raise AccountError("租户已停用")
    await redis.delete(sessions.REVOKE_SUB + account.sub)
    return _public(account)


async def change_password(sub: str, old_password: str, new_password: str) -> None:
    account = await Account.get(sub=sub)
    if not verify_password(old_password, account.password_hash):
        raise AccountError("旧密码验证错误")
    account.password_hash = get_password_hash(new_password)
    await account.save()


async def list_accounts(
    page: int = 1,
    page_size: int = 10,
    username: str = "",
    tenant_id: str = "",
    status: str = "",
) -> tuple[int, list[dict]]:
    query = Account.all()
    if username:
        query = query.filter(username__icontains=username)
    if tenant_id:
        member_subs = await TenantMember.filter(tenant_id=tenant_id).values_list("sub", flat=True)
        query = query.filter(Q(tenant_id=tenant_id) | Q(sub__in=member_subs))
    if status:
        query = query.filter(status=status)
    total = await query.count()
    rows = await query.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    members: dict[str, list[str]] = {}
    for m in await TenantMember.filter(sub__in=[row.sub for row in rows]).order_by("id"):
        members.setdefault(m.sub, []).append(m.tenant_id)
    tenant_ids = {row.tenant_id for row in rows} | {t for ids in members.values() for t in ids}
    tenants = {row.id: row.name for row in await Tenant.filter(id__in=tenant_ids)} if tenant_ids else {}
    return total, [
        _public(row)
        | {
            "tenant_name": tenants.get(row.tenant_id, row.tenant_id),
            "member_tenants": [{"id": t, "name": tenants.get(t, t)} for t in members.get(row.sub, [])],
            "created_at": row.created_at.strftime(settings.DATETIME_FORMAT),
        }
        for row in rows
    ]


async def list_tenants(
    page: int = 1, page_size: int = 10, name: str = "", ids: list[str] | None = None
) -> tuple[int, list[dict]]:
    query = Tenant.all() if ids is None else Tenant.filter(id__in=ids)
    if name:
        query = query.filter(name__icontains=name)
    total = await query.count()
    rows = await query.order_by("created_at").offset((page - 1) * page_size).limit(page_size)
    return total, [
        {"id": row.id, "name": row.name, "status": row.status, "created_at": row.created_at.strftime(settings.DATETIME_FORMAT)}
        for row in rows
    ]


async def tenant_names(ids: list[str]) -> list[tuple[str, str]]:
    names = dict(await Tenant.filter(id__in=ids).values_list("id", "name"))
    return [(i, names.get(i, i)) for i in ids]


async def tenant_is_active(tenant_id: str) -> bool:
    return await Tenant.filter(id=tenant_id, status="active").exists()


async def create_tenant(name: str) -> dict:
    """新建租户；内置控制台随租户开通（租户管理员需要登录控制台），其他应用仍按接入配置开通"""
    async with in_transaction("iam") as conn:
        tenant = await Tenant.create(using_db=conn, id="t_" + secrets.token_hex(8), name=name)
        console = await Client.select_for_update().using_db(conn).get(client_id=settings.CONSOLE_CLIENT_ID)
        console.tenants = [*console.tenants, tenant.id]
        await console.save(using_db=conn, update_fields=["tenants"])
    return {"id": tenant.id, "name": tenant.name, "status": tenant.status}


async def update_tenant(tenant_id: str, name: str, status: str) -> None:
    if tenant_id == SYSTEM_TENANT and status != "active":
        raise AccountError("系统租户不能停用")
    async with in_transaction("iam") as conn:
        tenant = await Tenant.select_for_update().using_db(conn).get_or_none(id=tenant_id)
        if not tenant:
            raise AccountError("租户不存在")
        tenant.name = name
        tenant.status = status
        await tenant.save(using_db=conn, update_fields=["name", "status"])
    await sessions.set_tenant_revoked(tenant_id, status == "disabled")


async def delete_tenant(tenant_id: str) -> None:
    """只删除已停用的空租户；吊销键保留到自然过期，避免旧令牌复活"""
    if tenant_id == SYSTEM_TENANT:
        raise AccountError("系统租户不能删除")
    async with in_transaction("iam") as conn:
        tenant = await Tenant.select_for_update().using_db(conn).get_or_none(id=tenant_id)
        if not tenant:
            raise AccountError("租户不存在")
        if tenant.status != "disabled":
            raise AccountError("请先停用租户")
        if await Account.filter(tenant_id=tenant_id).using_db(conn).exists():
            raise AccountError("租户下仍有身份账号")
        if await TenantMember.filter(tenant_id=tenant_id).using_db(conn).exists():
            raise AccountError("租户仍有跨租户成员")
        clients = await Client.select_for_update().using_db(conn).all()
        if any(tenant_id in c.tenants for c in clients if c.client_id != settings.CONSOLE_CLIENT_ID):
            raise AccountError("仍有接入应用开通该租户")
        for console in (c for c in clients if c.client_id == settings.CONSOLE_CLIENT_ID):
            console.tenants = [t for t in console.tenants if t != tenant_id]
            await console.save(using_db=conn, update_fields=["tenants"])
        await tenant.delete(using_db=conn)


async def _set_members(conn, sub: str, primary: str, member_ids: list[str], username: str, email: str | None) -> bool:
    """同步成员租户（主租户不重复记录）；新加入的租户发 user.created。返回是否移除了租户"""
    wanted = list(dict.fromkeys(t for t in member_ids if t != primary))
    current = set(await TenantMember.filter(sub=sub).using_db(conn).values_list("tenant_id", flat=True))
    added = [t for t in wanted if t not in current]
    if added and await Tenant.filter(id__in=added, status="active").using_db(conn).count() != len(added):
        raise AccountError("成员租户不存在或已停用")
    if SYSTEM_TENANT in wanted:
        raise AccountError("系统租户不能作为成员租户")
    removed = current - set(wanted)
    if removed:
        await TenantMember.filter(sub=sub, tenant_id__in=list(removed)).using_db(conn).delete()
    for tenant_id in added:
        await TenantMember.create(using_db=conn, sub=sub, tenant_id=tenant_id)
        await Outbox.create(
            using_db=conn,
            type="user.created",
            subject=sub,
            tenant_id=tenant_id,
            data={"sub": sub, "username": username, "email": email, "status": "active"},
        )
    # shortcut: 移出成员租户不发事件，只吊销会话；业务系统需要感知时增加 user.left 事件
    return bool(removed)


async def create_account(
    tenant_id: str,
    username: str,
    email: str | None,
    password: str,
    member_tenant_ids: list[str] | None = None,
    name: str | None = None,
    phone: str | None = None,
) -> dict:
    sub = new_sub()
    async with in_transaction("iam") as conn:
        tenant = await Tenant.select_for_update().using_db(conn).get_or_none(id=tenant_id)
        if not tenant or tenant.status != "active":
            raise AccountError("租户不存在或已停用")
        account = await Account.create(
            using_db=conn,
            sub=sub,
            tenant_id=tenant_id,
            username=username,
            email=email,
            name=name,
            phone=phone,
            password_hash=get_password_hash(password),
        )
        await Outbox.create(
            using_db=conn,
            type="user.created",
            subject=sub,
            tenant_id=tenant_id,
            data={"sub": sub, "username": username, "email": email, "status": "active"},
        )
        await _set_members(conn, sub, tenant_id, member_tenant_ids or [], username, email)
    return _public(account)


async def update_account(
    sub: str,
    tenant_id: str,
    username: str,
    email: str | None,
    status: str,
    password: str | None,
    member_tenant_ids: list[str] | None = None,
    name: str | None = None,
    phone: str | None = None,
) -> None:
    """member_tenant_ids 为 None 时不改成员租户"""
    async with in_transaction("iam") as conn:
        account = await Account.select_for_update().using_db(conn).get_or_none(sub=sub)
        if not account:
            raise AccountError("身份账号不存在")
        old_tenant_id, old_status = account.tenant_id, account.status
        tenant = await Tenant.select_for_update().using_db(conn).get_or_none(id=tenant_id)
        if not tenant or (tenant.status != "active" and tenant_id != old_tenant_id):
            raise AccountError("租户不存在或已停用")
        profile_changed = (account.tenant_id, account.username, account.email) != (tenant_id, username, email)
        fields = []
        if profile_changed:
            account.tenant_id, account.username, account.email = tenant_id, username, email
            fields.extend(["tenant_id", "username", "email"])
        # 姓名、电话只是账号资料，不发事件
        if (account.name, account.phone) != (name, phone):
            account.name, account.phone = name, phone
            fields.extend(["name", "phone"])
        if password:
            account.password_hash = get_password_hash(password)
            fields.append("password_hash")
        status_changed = old_status != status
        if status_changed:
            account.status = status
            fields.append("status")
        if fields:
            await account.save(using_db=conn, update_fields=[*fields, "updated_at"])
        if profile_changed:
            await Outbox.create(
                using_db=conn,
                type="user.updated",
                subject=sub,
                tenant_id=old_tenant_id,
                data={
                    "sub": sub,
                    "username": username,
                    "email": email,
                    "tenant_id": tenant_id,
                    "previous_tenant_id": old_tenant_id,
                    "status": status,
                },
            )
            if tenant_id != old_tenant_id:
                await Outbox.create(
                    using_db=conn,
                    type="user.created",
                    subject=sub,
                    tenant_id=tenant_id,
                    data={"sub": sub, "username": username, "email": email, "status": status},
                )
        if status_changed:
            await Outbox.create(
                using_db=conn,
                type="user.enabled" if status == "active" else "user.disabled",
                subject=sub,
                tenant_id=tenant_id,
                data={"sub": sub},
            )
        members_removed = False
        if member_tenant_ids is not None:
            members_removed = await _set_members(conn, sub, tenant_id, member_tenant_ids, username, email)
        elif tenant_id != old_tenant_id:
            await TenantMember.filter(sub=sub, tenant_id=tenant_id).using_db(conn).delete()

    if status == "disabled":
        await sessions.revoke_sub(sub)
    else:
        if old_status != "active":
            await redis.delete(sessions.REVOKE_SUB + sub)
        if password or tenant_id != old_tenant_id or members_removed:
            await sessions.revoke_sub(sub)


async def delete_account(sub: str) -> None:
    """只删除已停用账号；sub 不复用，向主租户和成员租户发 user.deleted"""
    async with in_transaction("iam") as conn:
        account = await Account.select_for_update().using_db(conn).get_or_none(sub=sub)
        if not account:
            raise AccountError("身份账号不存在")
        if account.status != "disabled":
            raise AccountError("请先停用账号")
        members = await TenantMember.filter(sub=sub).using_db(conn).values_list("tenant_id", flat=True)
        for tenant_id in [account.tenant_id, *members]:
            await Outbox.create(using_db=conn, type="user.deleted", subject=sub, tenant_id=tenant_id, data={"sub": sub})
        await TenantMember.filter(sub=sub).using_db(conn).delete()
        await account.delete(using_db=conn)
    await sessions.revoke_sub(sub)


async def authenticate_client(client_id: str, client_secret: str) -> Client | None:
    """机密客户端认证（client_secret 只存哈希）"""
    client = await Client.get_or_none(client_id=client_id, status="active")
    if not client or not client.client_secret_hash or not verify_password(client_secret, client.client_secret_hash):
        return None
    return client
