"""门户磁贴字段：iam.client.portal，控制台作为门户中的一个应用

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-29
"""

import json

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.settings.config import settings

    op.execute("""ALTER TABLE iam."client" ADD COLUMN "portal" JSONB NOT NULL DEFAULT '{}'""")
    # 控制台入口由门户前端直接跳首页，entry 仅表示在门户显示
    op.get_bind().execute(
        sa.text('UPDATE iam."client" SET portal = :portal WHERE client_id = :client_id'),
        dict(
            portal=json.dumps({"entry": "/", "icon": "KM", "description": "身份 · 能力 · 标注 · 运维", "order": 0}),
            client_id=settings.CONSOLE_CLIENT_ID,
        ),
    )


def downgrade() -> None:
    op.execute('ALTER TABLE iam."client" DROP COLUMN "portal"')
