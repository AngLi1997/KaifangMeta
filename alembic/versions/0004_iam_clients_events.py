"""应用接入字段（机密客户端、scope、租户开通、事件订阅）、事件 outbox / 投递、控制台事件去重

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27
"""

import json

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

IAM_SQL = """
ALTER TABLE "client"
    ADD COLUMN "type" VARCHAR(16) NOT NULL DEFAULT 'web',
    ADD COLUMN "grant_types" JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN "client_secret_hash" VARCHAR(255),
    ADD COLUMN "scopes" JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN "tenants" JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN "event_endpoint" VARCHAR(255),
    ADD COLUMN "event_secret" VARCHAR(128),
    ADD COLUMN "event_subscribe" JSONB NOT NULL DEFAULT '[]';
CREATE TABLE "outbox" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "type" VARCHAR(64) NOT NULL,
    "subject" VARCHAR(64) NOT NULL,
    "tenant_id" VARCHAR(32) NOT NULL,
    "data" JSONB NOT NULL,
    "dispatched" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_outbox_dispatc_d50639" ON "outbox" ("dispatched");
CREATE TABLE "delivery" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "outbox_id" BIGINT NOT NULL,
    "client_id" VARCHAR(64) NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'pending',
    "attempts" INT NOT NULL  DEFAULT 0,
    "next_attempt_at" TIMESTAMPTZ NOT NULL,
    "last_error" VARCHAR(500),
    "delivered_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_delivery_outbox__fbd0fc" UNIQUE ("outbox_id", "client_id")
);
CREATE INDEX "idx_delivery_outbox__4ef90c" ON "delivery" ("outbox_id");
CREATE INDEX "idx_delivery_client__798671" ON "delivery" ("client_id");
CREATE INDEX "idx_delivery_status_d37255" ON "delivery" ("status");
CREATE INDEX "idx_delivery_next_at_a34d79" ON "delivery" ("next_attempt_at");
"""

CONSOLE_SQL = """
CREATE TABLE "event_inbox" (
    "ce_id" VARCHAR(64) NOT NULL  PRIMARY KEY,
    "type" VARCHAR(64) NOT NULL,
    "received_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
"""


def upgrade() -> None:
    from app.settings.config import settings

    op.execute('SET LOCAL search_path TO "iam"')
    op.execute(IAM_SQL)
    op.execute("SET LOCAL search_path TO console_authz, public")
    op.execute(CONSOLE_SQL)
    # 控制台：web 应用、开通默认租户、订阅身份账号事件
    op.get_bind().execute(
        sa.text(
            """UPDATE iam.client SET grant_types = :grants, tenants = :tenants,
               event_endpoint = :endpoint, event_secret = :secret, event_subscribe = :subscribe
               WHERE client_id = :client_id"""
        ),
        dict(
            grants=json.dumps(["authorization_code", "refresh_token"]),
            tenants=json.dumps([settings.IAM_SYSTEM_TENANT]),
            endpoint=settings.CONSOLE_EVENT_ENDPOINT,
            secret=settings.CONSOLE_EVENT_SECRET,
            subscribe=json.dumps(["user.*"]),
            client_id=settings.CONSOLE_CLIENT_ID,
        ),
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "event_inbox"')
    op.execute('DROP TABLE IF EXISTS iam."delivery"')
    op.execute('DROP TABLE IF EXISTS iam."outbox"')
    op.execute(
        """ALTER TABLE iam."client" DROP COLUMN "type", DROP COLUMN "grant_types", DROP COLUMN "client_secret_hash",
           DROP COLUMN "scopes", DROP COLUMN "tenants", DROP COLUMN "event_endpoint", DROP COLUMN "event_secret",
           DROP COLUMN "event_subscribe\""""
    )
