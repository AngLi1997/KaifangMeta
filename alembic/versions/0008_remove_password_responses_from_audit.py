"""Remove password operation responses from audit detail.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-27
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """UPDATE "auditlog" SET response_body = NULL
           WHERE path LIKE '%/user/reset_password' OR path LIKE '%/base/update_password'"""
    )


def downgrade() -> None:
    # 清理后的密码操作响应无法安全恢复。
    pass
