"""保留唯一初始管理员、建立默认部门并为本地用户增加头像对象键

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    conn.execute(sa.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "avatar" VARCHAR(255)'))
    admin_id = conn.execute(
        sa.text('SELECT id FROM "user" WHERE username = :admin_username'),
        {"admin_username": settings.CONSOLE_ADMIN_USERNAME},
    ).scalar_one_or_none()
    if admin_id is None:
        raise RuntimeError("配置的控制台管理员不存在，已停止清理本地用户")
    conn.execute(
        sa.text('DELETE FROM "user" WHERE id <> :admin_id'),
        {"admin_id": admin_id},
    )
    dept_id = conn.execute(
        sa.text(
            '''INSERT INTO "dept" (name, "desc", is_deleted, "order", parent_id)
               VALUES ('开方数据', '默认部门', false, 0, 0)
               ON CONFLICT (name) DO UPDATE
               SET "desc" = EXCLUDED."desc", is_deleted = false, "order" = 0, parent_id = 0
               RETURNING id'''
        )
    ).scalar_one()
    conn.execute(
        sa.text(
            '''INSERT INTO "deptclosure" (ancestor, descendant, level)
               SELECT :dept_id, :dept_id, 0
               WHERE NOT EXISTS (
                   SELECT 1 FROM "deptclosure" WHERE ancestor = :dept_id AND descendant = :dept_id
               )'''
        ),
        {"dept_id": dept_id},
    )
    conn.execute(sa.text('UPDATE "user" SET dept_id = :dept_id'), {"dept_id": dept_id})


def downgrade() -> None:
    # 用户数据清理和部门数据不能安全逆转；移除头像字段时保留部门与剩余数据。
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS "avatar"')
