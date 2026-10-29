"""认证模块对其他模块的接口：身份账号基础字段与机构，不含角色或权限"""

import secrets

from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction

from app.core.redis import redis
from app.settings import settings
from app.utils.password import get_password_hash, verify_password

from . import sessions
from .models import Account, Client, Org, Outbox, Tenant, TenantMember

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
        "org_id": account.org_id,
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
    org_id: int | None = None,
) -> tuple[int, list[dict]]:
    query = Account.all()
    if org_id:
        query = query.filter(org_id=org_id)
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
    org_ids = {row.org_id for row in rows if row.org_id}
    orgs = dict(await Org.filter(id__in=org_ids).values_list("id", "name")) if org_ids else {}
    return total, [
        _public(row)
        | {
            "tenant_name": tenants.get(row.tenant_id, row.tenant_id),
            "org_name": orgs.get(row.org_id),
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


async def accessible_apps(sub: str, tid: str) -> list[dict]:
    """门户可见的应用：当前租户已开通；online 可进入，disabled 灰显维护中；按 order、名称排序"""
    # shortcut: 成员名单（access=members）与 testing 状态未实现，做成员名单时在此统一判定
    if tid not in await account_tenants(sub):
        return []
    apps = [
        {"client_id": c.client_id, "name": c.name, "type": c.type, "status": c.status, **c.portal}
        for c in await Client.filter(status__in=["online", "disabled"])
        if tid in c.tenants and c.portal.get("entry")
    ]
    return sorted(apps, key=lambda a: (a.get("order", 100), a["name"]))


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
    org_id: int | None = None,
) -> dict:
    sub = new_sub()
    async with in_transaction("iam") as conn:
        tenant = await Tenant.select_for_update().using_db(conn).get_or_none(id=tenant_id)
        if not tenant or tenant.status != "active":
            raise AccountError("租户不存在或已停用")
        await _check_account_org(conn, tenant_id, org_id)
        account = await Account.create(
            org_id=org_id,
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
            data={"sub": sub, "username": username, "email": email, "org_id": org_id, "status": "active"},
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
    org_id: int | None = None,
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
        if org_id != account.org_id or tenant_id != old_tenant_id:
            await _check_account_org(conn, tenant_id, org_id, allow_disabled=org_id == account.org_id)
        profile = (tenant_id, username, email, org_id)
        profile_changed = (account.tenant_id, account.username, account.email, account.org_id) != profile
        fields = []
        if profile_changed:
            account.tenant_id, account.username, account.email, account.org_id = profile
            fields.extend(["tenant_id", "username", "email", "org_id"])
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
                    "org_id": org_id,
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
    client = await Client.get_or_none(client_id=client_id, status="online")
    if not client or not client.client_secret_hash or not verify_password(client_secret, client.client_secret_hash):
        return None
    return client


# ---- 机构（docs/platform/auth/identity.md「机构」）----


async def _check_account_org(conn, tenant_id: str, org_id: int | None, allow_disabled: bool = False) -> None:
    if org_id is None:
        return
    org = await Org.filter(id=org_id, tenant_id=tenant_id).using_db(conn).first()
    if not org or (org.status != "active" and not allow_disabled):
        raise AccountError("所属机构不存在、已停用或不属于主租户")


def _org_public(org: Org, level: int) -> dict:
    return {
        "id": org.id,
        "parent_id": org.parent_id,
        "code": org.code,
        "name": org.name,
        "level": level,
        "sort_order": org.sort_order,
        "status": org.status,
    }


def _levels(orgs: list[Org]) -> dict[int, int]:
    """按 parent_id 计算深度（根为 1）；上级缺失按根处理，环上的节点不返回"""
    by_id = {o.id: o for o in orgs}
    levels: dict[int, int] = {}
    for org in orgs:
        chain, node = [], org
        while node and node.id not in levels and node not in chain:
            chain.append(node)
            node = by_id.get(node.parent_id) if node.parent_id else None
        if node in chain:
            continue
        base = levels[node.id] if node else 0
        for i, item in enumerate(reversed(chain), 1):
            levels[item.id] = base + i
    return levels


async def list_orgs(tenant_id: str) -> list[dict]:
    """租户机构平铺列表（含 level），按层级、排序、ID 排列"""
    orgs = await Org.filter(tenant_id=tenant_id)
    levels = _levels(orgs)
    rows = [_org_public(o, levels[o.id]) for o in orgs if o.id in levels]
    return sorted(rows, key=lambda r: (r["level"], r["sort_order"], r["id"]))


async def org_tree(tenant_id: str) -> list[dict]:
    rows = await list_orgs(tenant_id)
    counts = dict(
        await Account.filter(tenant_id=tenant_id, org_id__isnull=False)
        .group_by("org_id")
        .annotate(n=Count("sub"))
        .values_list("org_id", "n")
    )
    nodes = {r["id"]: r | {"account_count": counts.get(r["id"], 0), "children": []} for r in rows}
    roots = []
    for node in nodes.values():
        parent = nodes.get(node["parent_id"])
        (parent["children"] if parent else roots).append(node)
    return roots


async def _check_parent(conn, tenant_id: str, org_id: int | None, parent_id: int | None) -> None:
    if parent_id is None:
        return
    orgs = {o.id: o for o in await Org.filter(tenant_id=tenant_id).using_db(conn)}
    if parent_id not in orgs:
        raise AccountError("上级机构不存在")
    node = orgs[parent_id]
    while node:
        if node.id == org_id:
            raise AccountError("不能移到自身或下级机构下")
        node = orgs.get(node.parent_id) if node.parent_id else None


async def _org_event(conn, tenant_id: str, org_id: int) -> None:
    await Outbox.create(
        using_db=conn, type="org.changed", subject=str(org_id), tenant_id=tenant_id,
        data={"tenant_id": tenant_id, "org_id": org_id},
    )


async def create_org(tenant_id: str, parent_id: int | None, code: str, name: str, sort_order: int) -> dict:
    async with in_transaction("iam") as conn:
        await _check_parent(conn, tenant_id, None, parent_id)
        if await Org.filter(tenant_id=tenant_id, code=code).using_db(conn).exists():
            raise AccountError("机构编码已存在")
        org = await Org.create(
            using_db=conn, tenant_id=tenant_id, parent_id=parent_id, code=code, name=name, sort_order=sort_order
        )
        await _org_event(conn, tenant_id, org.id)
    return {"id": org.id}


async def update_org(
    tenant_id: str, org_id: int, parent_id: int | None, code: str, name: str, sort_order: int, status: str
) -> None:
    async with in_transaction("iam") as conn:
        org = await Org.select_for_update().using_db(conn).get_or_none(id=org_id, tenant_id=tenant_id)
        if not org:
            raise AccountError("机构不存在")
        if parent_id != org.parent_id:
            await _check_parent(conn, tenant_id, org_id, parent_id)
        if code != org.code and await Org.filter(tenant_id=tenant_id, code=code).using_db(conn).exists():
            raise AccountError("机构编码已存在")
        org.parent_id, org.code, org.name, org.sort_order, org.status = parent_id, code, name, sort_order, status
        await org.save(using_db=conn)
        await _org_event(conn, tenant_id, org_id)


async def delete_org(tenant_id: str, org_id: int) -> None:
    async with in_transaction("iam") as conn:
        org = await Org.select_for_update().using_db(conn).get_or_none(id=org_id, tenant_id=tenant_id)
        if not org:
            raise AccountError("机构不存在")
        if org.status != "disabled":
            raise AccountError("请先停用机构")
        if await Org.filter(parent_id=org_id).using_db(conn).exists():
            raise AccountError("机构下仍有下级机构")
        if await Account.filter(org_id=org_id).using_db(conn).exists():
            raise AccountError("机构下仍有身份账号")
        await org.delete(using_db=conn)
        await _org_event(conn, tenant_id, org_id)


async def import_orgs(tenant_id: str, rows: list[dict]) -> int:
    """按 id 新增或更新（保留存量系统的机构 ID），完成后把序列调到最大 ID 之后"""
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise AccountError("导入数据中机构 ID 重复")
    codes = [r["code"] for r in rows]
    if len(set(codes)) != len(codes):
        raise AccountError("导入数据中机构编码重复")
    async with in_transaction("iam") as conn:
        existing = {o.id: o for o in await Org.filter(id__in=ids).using_db(conn)}
        if any(o.tenant_id != tenant_id for o in existing.values()):
            raise AccountError("机构 ID 已被其他租户使用")
        taken = await Org.filter(tenant_id=tenant_id, code__in=codes).exclude(id__in=ids).using_db(conn).exists()
        if taken:
            raise AccountError("机构编码与已有机构重复")
        known = set(ids) | set(await Org.filter(tenant_id=tenant_id).using_db(conn).values_list("id", flat=True))
        if any(r["parent_id"] is not None and r["parent_id"] not in known for r in rows):
            raise AccountError("上级机构不存在")
        for r in rows:
            org = existing.get(r["id"]) or Org(id=r["id"], tenant_id=tenant_id)
            org.parent_id, org.code, org.name = r["parent_id"], r["code"], r["name"]
            org.sort_order, org.status = r["sort_order"], r["status"]
            await org.save(using_db=conn, force_create=r["id"] not in existing)
        if _levels(await Org.filter(tenant_id=tenant_id).using_db(conn)).keys() != set(
            await Org.filter(tenant_id=tenant_id).using_db(conn).values_list("id", flat=True)
        ):
            raise AccountError("机构上下级存在循环")
        await conn.execute_query(
            "SELECT setval(pg_get_serial_sequence('iam.org', 'id'), GREATEST((SELECT max(id) FROM iam.org), 1))"
        )
        await Outbox.create(
            using_db=conn, type="org.changed", subject="import", tenant_id=tenant_id,
            data={"tenant_id": tenant_id, "org_id": None},
        )
    return len(rows)
