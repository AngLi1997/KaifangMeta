"""移除平台控制台部门菜单；业务组织由业务系统维护

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-27
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('DELETE FROM "menu" WHERE path = \'dept\' AND component = \'/system/dept\'')


def downgrade() -> None:
    # shortcut: customized grants cannot be reconstructed; add a restoring migration if the department UI returns.
    pass
