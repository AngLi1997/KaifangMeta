"""应用接入：iam.client 网关配置、网关密钥、下发状态，状态改为 online / disabled，菜单与接口权限

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-29
"""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

APIS = [
    ("GET", "/app/list", "查看接入应用"),
    ("GET", "/app/get", "查看接入应用详情"),
    ("POST", "/app/create", "注册应用"),
    ("POST", "/app/update", "修改应用"),
    ("POST", "/app/status", "上线或停用应用"),
    ("POST", "/app/sync", "下发应用网关配置"),
    ("POST", "/app/secret/rotate", "轮换应用密钥"),
]


def upgrade() -> None:
    from app.settings.config import settings

    op.execute(
        """ALTER TABLE iam."client" ADD COLUMN "gateway" JSONB NOT NULL DEFAULT '{}';
        ALTER TABLE iam."client" ADD COLUMN "gateway_secret" VARCHAR(128);
        ALTER TABLE iam."client" ADD COLUMN "owner" VARCHAR(64);
        ALTER TABLE iam."client" ADD COLUMN "sync_status" VARCHAR(16);
        ALTER TABLE iam."client" ADD COLUMN "synced_at" TIMESTAMPTZ;
        UPDATE iam."client" SET status = CASE WHEN status = 'active' THEN 'online' ELSE 'disabled' END;
        ALTER TABLE iam."client" ALTER COLUMN "status" SET DEFAULT 'online';"""
    )
    conn = op.get_bind()
    system_id = conn.execute(sa.text('SELECT id FROM "menu" WHERE path = \'/system\'')).scalar_one()
    # 放在租户管理之后
    tenant_order = conn.execute(
        sa.text('SELECT "order" FROM "menu" WHERE parent_id = :pid AND path = \'tenant\''), {"pid": system_id}
    ).scalar_one()
    conn.execute(
        sa.text('UPDATE "menu" SET "order" = "order" + 1 WHERE parent_id = :pid AND "order" > :o'),
        {"pid": system_id, "o": tenant_order},
    )
    menu_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
               VALUES ('menu', '应用接入', 'app', :o, :pid, 'icon-park-outline:application-two', false, '/system/app', false)
               RETURNING id"""
        ),
        {"pid": system_id, "o": tenant_order + 1},
    ).scalar_one()
    conn.execute(
        sa.text('INSERT INTO "role_menu" (role_id, menu_id) SELECT id, :mid FROM "role" WHERE name = \'管理员\' '
                "ON CONFLICT DO NOTHING"),
        {"mid": menu_id},
    )
    for method, suffix, summary in APIS:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        conn.execute(
            sa.text(
                """INSERT INTO "api" (method, path, summary, tags)
                   SELECT CAST(:method AS varchar), CAST(:path AS varchar), CAST(:summary AS varchar), '应用接入'
                   WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = :method AND path = :path)"""
            ),
            {"method": method, "path": path, "summary": summary},
        )
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a
                   WHERE r.name = '管理员' AND a.method = :method AND a.path = :path
                   ON CONFLICT DO NOTHING"""
            ),
            {"method": method, "path": path},
        )


def downgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    for method, suffix, _ in APIS:
        conn.execute(
            sa.text('DELETE FROM "api" WHERE method = :method AND path = :path'),
            {"method": method, "path": f"{settings.API_PREFIX}/v1{suffix}"},
        )
    order = conn.execute(sa.text('SELECT "order" FROM "menu" WHERE path = \'app\' AND component = \'/system/app\'')).scalar()
    conn.execute(sa.text('DELETE FROM "menu" WHERE path = \'app\' AND component = \'/system/app\''))
    if order is not None:
        conn.execute(
            sa.text('UPDATE "menu" SET "order" = "order" - 1 WHERE parent_id = '
                    '(SELECT id FROM "menu" WHERE path = \'/system\') AND "order" > :o'),
            {"o": order},
        )
    op.execute(
        """UPDATE iam."client" SET status = CASE WHEN status = 'online' THEN 'active' ELSE 'disabled' END;
        ALTER TABLE iam."client" ALTER COLUMN "status" SET DEFAULT 'active';
        ALTER TABLE iam."client" DROP COLUMN "gateway", DROP COLUMN "gateway_secret", DROP COLUMN "owner",
            DROP COLUMN "sync_status", DROP COLUMN "synced_at";"""
    )
