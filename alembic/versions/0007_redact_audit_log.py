"""Remove sensitive values from stored audit request and response bodies.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op
from app.utils.audit import redact_sensitive_data

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    update_stmt = sa.text(
        'UPDATE "auditlog" SET request_args = :request_args, response_body = :response_body WHERE id = :id'
    ).bindparams(
        sa.bindparam("request_args", type_=JSONB(none_as_null=True)),
        sa.bindparam("response_body", type_=JSONB(none_as_null=True)),
    )
    last_id = 0
    while rows := conn.execute(
        sa.text(
            'SELECT id, request_args, response_body FROM "auditlog" '
            'WHERE id > :last_id ORDER BY id LIMIT 500'
        ),
        {"last_id": last_id},
    ).mappings().all():
        updates = []
        for row in rows:
            request_args = redact_sensitive_data(row["request_args"])
            response_body = redact_sensitive_data(row["response_body"])
            if request_args != row["request_args"] or response_body != row["response_body"]:
                updates.append(
                    {"id": row["id"], "request_args": request_args, "response_body": response_body}
                )
        if updates:
            conn.execute(update_stmt, updates)
        last_id = rows[-1]["id"]


def downgrade() -> None:
    # 已清理的日志明细无法安全恢复。
    pass
