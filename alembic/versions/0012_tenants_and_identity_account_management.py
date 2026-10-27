"""租户与身份账号管理菜单和接口权限

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    system_id = conn.execute(sa.text('SELECT id FROM "menu" WHERE path = \'/system\'')).scalar_one()
    conn.execute(
        sa.text('UPDATE "menu" SET "order" = "order" + 1 WHERE parent_id = :pid AND "order" >= 2'),
        {"pid": system_id},
    )
    tenant_menu_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
               SELECT 'menu', '租户管理', 'tenant', 2, :pid, 'icon-park-outline:building-two', false,
                      '/system/tenant', false
               WHERE NOT EXISTS (SELECT 1 FROM "menu" WHERE path = 'tenant' AND component = '/system/tenant')
               RETURNING id"""
        ),
        {"pid": system_id},
    ).scalar_one_or_none()
    if tenant_menu_id is None:
        tenant_menu_id = conn.execute(
            sa.text('SELECT id FROM "menu" WHERE path = \'tenant\' AND component = \'/system/tenant\'')
        ).scalar_one()
    conn.execute(
        sa.text(
            'INSERT INTO "role_menu" (role_id, menu_id) '
            'SELECT id, :mid FROM "role" WHERE name = \'管理员\' ON CONFLICT DO NOTHING'
        ),
        {"mid": tenant_menu_id},
    )

    apis = [
        ("POST", "/account/create", "新建身份账号", "身份账号"),
        ("POST", "/account/update", "修改身份账号", "身份账号"),
        ("GET", "/tenant/list", "查看租户列表", "租户"),
        ("POST", "/tenant/create", "新建租户", "租户"),
        ("POST", "/tenant/update", "修改租户", "租户"),
    ]
    paths = []
    for method, suffix, summary, tags in apis:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        paths.append(path)
        conn.execute(
            sa.text(
                """INSERT INTO "api" (method, path, summary, tags)
                   SELECT CAST(:method AS varchar), CAST(:path AS varchar), CAST(:summary AS varchar), CAST(:tags AS varchar)
                   WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = :method AND path = :path)"""
            ),
            {"method": method, "path": path, "summary": summary, "tags": tags},
        )

    member_path = f"{settings.API_PREFIX}/v1/user/list"
    for path in [f"{settings.API_PREFIX}/v1/account/list", member_path, *paths]:
        conn.execute(
            sa.text(
                """DELETE FROM "role_api" ra USING "role" r, "api" a
                   WHERE ra.role_id = r.id AND ra.api_id = a.id AND r.name <> '管理员' AND a.path = :path"""
            ),
            {"path": path},
        )
    for path in [member_path, *paths]:
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a
                   WHERE r.name = '管理员' AND a.path = :path
                   ON CONFLICT DO NOTHING"""
            ),
            {"path": path},
        )


def downgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    for suffix in ["/account/create", "/account/update", "/tenant/list", "/tenant/create", "/tenant/update"]:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        conn.execute(
            sa.text('DELETE FROM "role_api" WHERE api_id IN (SELECT id FROM "api" WHERE path = :path)'),
            {"path": path},
        )
    for suffix in ["/account/list", "/user/list"]:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a WHERE a.path = :path
                   ON CONFLICT DO NOTHING"""
            ),
            {"path": path},
        )
    conn.execute(sa.text('DELETE FROM "menu" WHERE path = \'tenant\' AND component = \'/system/tenant\''))
    conn.execute(
        sa.text('UPDATE "menu" SET "order" = "order" - 1 WHERE parent_id = '
                '(SELECT id FROM "menu" WHERE path = \'/system\') AND "order" >= 3')
    )
