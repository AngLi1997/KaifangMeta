"""控制台只保留配置的管理员成员

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    admin_id = conn.execute(
        sa.text('SELECT id FROM "user" WHERE username = :admin_username'),
        {"admin_username": settings.CONSOLE_ADMIN_USERNAME},
    ).scalar_one_or_none()
    if admin_id is None:
        raise RuntimeError("配置的控制台管理员成员不存在，已停止清理本地用户")
    conn.execute(
        sa.text('DELETE FROM "user" WHERE id <> :admin_id'),
        {"admin_id": admin_id},
    )
    conn.execute(
        sa.text('UPDATE "menu" SET name = :name WHERE path = \'user\' AND component = \'/system/user\''),
        {"name": "控制台成员"},
    )


def downgrade() -> None:
    # shortcut: deleted console memberships cannot be reconstructed; restore them from a backup if required.
    pass
