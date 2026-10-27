"""删除租户与身份账号的接口权限

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

# 租户管理员与编辑账号一致，可删除本租户账号；删除租户只授予管理员
APIS = [
    ("DELETE", "/account/delete", "删除身份账号", "身份账号", ["管理员", "租户管理员"]),
    ("DELETE", "/tenant/delete", "删除租户", "租户", ["管理员"]),
]


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    for method, suffix, summary, tags, roles in APIS:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        conn.execute(
            sa.text(
                """INSERT INTO "api" (method, path, summary, tags)
                   SELECT CAST(:method AS varchar), CAST(:path AS varchar), CAST(:summary AS varchar), CAST(:tags AS varchar)
                   WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = :method AND path = :path)"""
            ),
            {"method": method, "path": path, "summary": summary, "tags": tags},
        )
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a
                   WHERE r.name = ANY(:roles) AND a.method = :method AND a.path = :path
                   ON CONFLICT DO NOTHING"""
            ),
            {"method": method, "path": path, "roles": roles},
        )


def downgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    for method, suffix, *_ in APIS:
        conn.execute(
            sa.text('DELETE FROM "api" WHERE method = :method AND path = :path'),
            {"method": method, "path": f"{settings.API_PREFIX}/v1{suffix}"},
        )
