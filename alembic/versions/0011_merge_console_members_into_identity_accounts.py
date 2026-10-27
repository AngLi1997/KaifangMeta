"""身份账号页合并控制台成员信息，移除重复菜单

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-27
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('DELETE FROM "menu" WHERE path = \'user\' AND component = \'/system/user\'')
    op.execute('UPDATE "menu" SET "order" = 1 WHERE path = \'account\' AND component = \'/system/account\'')
    op.execute(
        'UPDATE "menu" SET redirect = \'/system/account\' '
        'WHERE path = \'/system\' AND redirect = \'/system/user\''
    )


def downgrade() -> None:
    # shortcut: the former menu grants and customized fields cannot be reconstructed safely.
    pass
