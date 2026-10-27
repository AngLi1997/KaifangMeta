"""认证模块身份表（iam schema）

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# 由 app/iam/models 的 Tortoise 模型生成（tortoise.utils.get_schema_sql），与 ORM 字段保持一致
SCHEMA_SQL = """
CREATE TABLE "account" (
    "sub" VARCHAR(32) NOT NULL  PRIMARY KEY,
    "tenant_id" VARCHAR(32) NOT NULL,
    "username" VARCHAR(64) NOT NULL UNIQUE,
    "email" VARCHAR(255),
    "password_hash" VARCHAR(255) NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'active',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_account_tenant__126fd8" ON "account" ("tenant_id");
CREATE INDEX "idx_account_status_d97dc0" ON "account" ("status");
COMMENT ON TABLE "account" IS '身份账号：登录名、凭据、全局唯一且不复用的 sub、启停状态';
CREATE TABLE "client" (
    "client_id" VARCHAR(64) NOT NULL  PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "redirect_uris" JSONB NOT NULL,
    "post_logout_redirect_uris" JSONB NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'active',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "client" IS '接入应用（OIDC client），控制台为内置应用 kaifang-meta-console';
CREATE TABLE "signing_key" (
    "kid" VARCHAR(32) NOT NULL  PRIMARY KEY,
    "private_pem" TEXT NOT NULL,
    "public_jwk" JSONB NOT NULL,
    "active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "signing_key" IS 'Token 签名密钥，kid 轮换时新旧并存，JWKS 公布全部未退役公钥';
CREATE TABLE "tenant" (
    "id" VARCHAR(32) NOT NULL  PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'active',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
"""

TABLES = ["account", "client", "signing_key", "tenant"]


def upgrade() -> None:
    # 认证模块独立 schema，与控制台权限表隔离，仅按 sub 关联
    op.execute('CREATE SCHEMA IF NOT EXISTS "iam"')
    op.execute('SET LOCAL search_path TO "iam"')
    op.execute(SCHEMA_SQL)
    op.execute("SET LOCAL search_path TO console_authz, public")


def downgrade() -> None:
    op.execute('DROP SCHEMA IF EXISTS "iam" CASCADE')
