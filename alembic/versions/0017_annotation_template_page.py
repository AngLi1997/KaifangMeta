"""场景模板编辑改为独立页面：隐藏菜单「模板编辑」与模板详情接口

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

ROLES = ["管理员", "租户管理员"]


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    menu_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
               SELECT 'menu', '模板编辑', 'template-edit', 5, id, 'icon-park-outline:page-template', true,
                      '/annotation/template-edit', false
               FROM "menu" WHERE path = '/annotation' AND menu_type = 'catalog'
               RETURNING id"""
        )
    ).scalar_one()
    path = f"{settings.API_PREFIX}/v1/annotation/template/get"
    # 平台启动时会把新接口同步进 api 表，这里先查后插，避免重复
    conn.execute(
        sa.text(
            """INSERT INTO "api" (method, path, summary, tags)
               SELECT 'GET', CAST(:path AS varchar), '查看场景模板', '数据标注'
               WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = 'GET' AND path = :path)"""
        ),
        {"path": path},
    )
    api_id = conn.execute(
        sa.text("""SELECT min(id) FROM "api" WHERE method = 'GET' AND path = :path"""), {"path": path}
    ).scalar_one()
    for role in ROLES:
        params = {"role": role, "menu_id": menu_id, "api_id": api_id}
        conn.execute(
            sa.text(
                'INSERT INTO "role_menu" (role_id, menu_id) '
                'SELECT id, :menu_id FROM "role" WHERE name = :role ON CONFLICT DO NOTHING'
            ),
            params,
        )
        conn.execute(
            sa.text(
                'INSERT INTO "role_api" (role_id, api_id) '
                'SELECT id, :api_id FROM "role" WHERE name = :role ON CONFLICT DO NOTHING'
            ),
            params,
        )


def downgrade() -> None:
    from app.settings.config import settings

    op.execute("""DELETE FROM "menu" WHERE path = 'template-edit' AND component = '/annotation/template-edit'""")
    op.execute(f"""DELETE FROM "api" WHERE method = 'GET' AND path = '{settings.API_PREFIX}/v1/annotation/template/get'""")
