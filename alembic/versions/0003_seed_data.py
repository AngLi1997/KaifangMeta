"""初始化 seed：默认租户、控制台应用、签名密钥、首个超管（身份账号 + 控制台本地用户）、菜单、API、角色

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27
"""

import json

import sqlalchemy as sa
from fastapi.routing import APIRoute

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SYSTEM_MENUS = [
    ("角色管理", "role", "carbon:user-role", "/system/role"),
    ("菜单管理", "menu", "material-symbols:list-alt-outline", "/system/menu"),
    ("API管理", "api", "ant-design:api-outlined", "/system/api"),
    ("审计日志", "auditlog", "ph:clipboard-text-bold", "/system/auditlog"),
]


def _insert(conn, table: str, row: dict, returning: str | None = "id"):
    cols = ", ".join(f'"{k}"' for k in row)
    vals = ", ".join(f":{k}" for k in row)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})" + (f" RETURNING {returning}" if returning else "")
    result = conn.execute(sa.text(sql), row)
    return result.scalar_one() if returning else None


def _menu(conn, **kw) -> int:
    row = dict(remark=None, is_hidden=False, keepalive=False, redirect=None) | kw
    return _insert(conn, '"menu"', row)


def _route_apis() -> list[dict]:
    # 与 ApiController.refresh_api 相同的规则：只登记带鉴权依赖的接口
    from app import app

    return [
        dict(method=list(r.methods)[0], path=r.path_format, summary=r.summary, tags=list(r.tags)[0])
        for r in app.routes
        if isinstance(r, APIRoute) and len(r.dependencies) > 0
    ]


def _seed_iam(conn) -> str:
    """认证模块：租户、控制台 client、签名密钥、首个超管身份账号；返回其 sub"""
    from app.iam.keys import generate_key
    from app.iam.service import new_sub
    from app.settings.config import settings
    from app.utils.password import get_password_hash

    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]  # noqa: E731
    _insert(conn, "iam.tenant", dict(id=settings.IAM_SYSTEM_TENANT, name="系统租户"), returning=None)
    _insert(
        conn,
        "iam.client",
        dict(
            client_id=settings.CONSOLE_CLIENT_ID,
            name="平台控制台",
            redirect_uris=json.dumps(split(settings.CONSOLE_REDIRECT_URIS)),
            post_logout_redirect_uris=json.dumps(split(settings.CONSOLE_POST_LOGOUT_REDIRECT_URIS)),
        ),
        returning=None,
    )
    kid, private_pem, public_jwk = generate_key()
    _insert(
        conn,
        "iam.signing_key",
        dict(kid=kid, private_pem=private_pem, public_jwk=json.dumps(public_jwk)),
        returning=None,
    )
    sub = new_sub()
    _insert(
        conn,
        "iam.account",
        dict(
            sub=sub,
            tenant_id=settings.IAM_SYSTEM_TENANT,
            username=settings.CONSOLE_ADMIN_USERNAME,
            email=settings.CONSOLE_ADMIN_EMAIL,
            password_hash=get_password_hash(settings.CONSOLE_ADMIN_PASSWORD),
        ),
        returning=None,
    )
    return sub


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    admin_sub = _seed_iam(conn)

    # 控制台：按 sub 建本地超管（docs/platform/auth/authz.md「第一个平台超级管理员」）
    _insert(
        conn,
        '"user"',
        dict(
            sub=admin_sub,
            username=settings.CONSOLE_ADMIN_USERNAME,
            email=settings.CONSOLE_ADMIN_EMAIL,
            is_active=True,
            is_superuser=True,
        ),
    )

    system_id = _menu(
        conn,
        menu_type="catalog",
        name="系统管理",
        path="/system",
        order=1,
        parent_id=0,
        icon="carbon:gui-management",
        component="Layout",
        redirect="/system/account",
    )
    menu_ids = [system_id]
    for order, (name, path, icon, component) in enumerate(SYSTEM_MENUS, start=2):
        menu_ids.append(
            _menu(
                conn,
                menu_type="menu",
                name=name,
                path=path,
                order=order,
                parent_id=system_id,
                icon=icon,
                component=component,
            )
        )
    menu_ids.append(
        _menu(
            conn,
            menu_type="menu",
            name="一级菜单",
            path="/top-menu",
            order=2,
            parent_id=0,
            icon="material-symbols:featured-play-list-outline",
            component="/top-menu",
            redirect="",
        )
    )

    apis = _route_apis()
    api_ids = [_insert(conn, '"api"', api) for api in apis]
    basic_api_ids = [i for i, a in zip(api_ids, apis) if a["method"] == "GET" or a["tags"] == "基础模块"]

    admin_role = _insert(conn, '"role"', dict(name="管理员", desc="管理员角色"))
    user_role = _insert(conn, '"role"', dict(name="普通用户", desc="普通用户角色"))

    role_menu = sa.table("role_menu", sa.column("role_id"), sa.column("menu_id"))
    role_api = sa.table("role_api", sa.column("role_id"), sa.column("api_id"))
    op.bulk_insert(role_menu, [{"role_id": r, "menu_id": m} for r in (admin_role, user_role) for m in menu_ids])
    op.bulk_insert(
        role_api,
        [{"role_id": admin_role, "api_id": a} for a in api_ids]
        + [{"role_id": user_role, "api_id": a} for a in basic_api_ids],
    )


def downgrade() -> None:
    for table in ['"user_role"', '"role_api"', '"role_menu"', '"user"', '"role"', '"menu"', '"api"']:
        op.execute(f"DELETE FROM {table}")
    for table in ["iam.account", "iam.signing_key", "iam.client", "iam.tenant"]:
        op.execute(f"DELETE FROM {table}")
