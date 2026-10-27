"""身份账号姓名、电话

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-27
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE "iam"."account" ADD COLUMN "name" VARCHAR(64), ADD COLUMN "phone" VARCHAR(20)')


def downgrade() -> None:
    op.execute('ALTER TABLE "iam"."account" DROP COLUMN "name", DROP COLUMN "phone"')
