"""运维看板外链与 APISIX / etcd 控制台

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu", sa.Column("href", sa.String(length=500), nullable=True))
    conn = op.get_bind()
    ops_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive, redirect)
               VALUES ('catalog', '运维看板', '/ops', 2, 0, 'icon-park-outline:setting-two', false, 'Layout', false, '/workbench')
               RETURNING id"""
        )
    ).scalar_one()
    menu_ids = [ops_id]
    for name, path, url, order, icon in [
        ("MinIO", "minio", "http://localhost:9001", 1, "icon-park-outline:cloud-storage"),
        ("APISIX", "apisix", "http://localhost:9180/ui/", 2, "icon-park-outline:api"),
        ("ETCD", "etcd", "http://localhost:9010", 3, "icon-park-outline:database-network"),
    ]:
        menu_ids.append(
            conn.execute(
                sa.text(
                    """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive, href)
                       VALUES ('menu', :name, :path, :order, :pid, :icon, false, '', false, :href)
                       RETURNING id"""
                ),
                {"name": name, "path": path, "order": order, "pid": ops_id, "icon": icon, "href": url},
            ).scalar_one()
        )
    for menu_id in menu_ids:
        conn.execute(
            sa.text(
                'INSERT INTO "role_menu" (role_id, menu_id) '
                'SELECT id, :menu_id FROM "role" WHERE name = \'管理员\' ON CONFLICT DO NOTHING'
            ),
            {"menu_id": menu_id},
        )


def downgrade() -> None:
    op.execute(
        'DELETE FROM "menu" WHERE parent_id = '
        '(SELECT id FROM "menu" WHERE path = \'/ops\' AND menu_type = \'catalog\') OR path = \'/ops\''
    )
    op.drop_column("menu", "href")
