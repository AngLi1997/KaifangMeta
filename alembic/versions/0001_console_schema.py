"""控制台权限表（console_authz schema）

Revision ID: 0001
Revises: 
Create Date: 2026-10-27
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# 由 app/models 的 Tortoise 模型生成（tortoise.utils.get_schema_sql），与 ORM 字段保持一致
SCHEMA_SQL = """
CREATE TABLE "api" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "path" VARCHAR(100) NOT NULL,
    "method" VARCHAR(6) NOT NULL,
    "summary" VARCHAR(500) NOT NULL,
    "tags" VARCHAR(100) NOT NULL
);
CREATE INDEX "idx_api_created_78d19f" ON "api" ("created_at");
CREATE INDEX "idx_api_updated_643c8b" ON "api" ("updated_at");
CREATE INDEX "idx_api_path_9ed611" ON "api" ("path");
CREATE INDEX "idx_api_method_a46dfb" ON "api" ("method");
CREATE INDEX "idx_api_summary_400f73" ON "api" ("summary");
CREATE INDEX "idx_api_tags_04ae27" ON "api" ("tags");
COMMENT ON COLUMN "api"."path" IS 'API路径';
COMMENT ON COLUMN "api"."method" IS '请求方法';
COMMENT ON COLUMN "api"."summary" IS '请求简介';
COMMENT ON COLUMN "api"."tags" IS 'API标签';
CREATE TABLE "auditlog" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL,
    "username" VARCHAR(64) NOT NULL  DEFAULT '',
    "module" VARCHAR(64) NOT NULL  DEFAULT '',
    "summary" VARCHAR(128) NOT NULL  DEFAULT '',
    "method" VARCHAR(10) NOT NULL  DEFAULT '',
    "path" VARCHAR(255) NOT NULL  DEFAULT '',
    "status" INT NOT NULL  DEFAULT -1,
    "response_time" INT NOT NULL  DEFAULT 0,
    "request_args" JSONB,
    "response_body" JSONB
);
CREATE INDEX "idx_auditlog_created_cc33d0" ON "auditlog" ("created_at");
CREATE INDEX "idx_auditlog_updated_2f871f" ON "auditlog" ("updated_at");
CREATE INDEX "idx_auditlog_user_id_4b93fa" ON "auditlog" ("user_id");
CREATE INDEX "idx_auditlog_usernam_b187b3" ON "auditlog" ("username");
CREATE INDEX "idx_auditlog_module_04058b" ON "auditlog" ("module");
CREATE INDEX "idx_auditlog_summary_3e27da" ON "auditlog" ("summary");
CREATE INDEX "idx_auditlog_method_4270a2" ON "auditlog" ("method");
CREATE INDEX "idx_auditlog_path_b99502" ON "auditlog" ("path");
CREATE INDEX "idx_auditlog_status_2a72d2" ON "auditlog" ("status");
CREATE INDEX "idx_auditlog_respons_8caa87" ON "auditlog" ("response_time");
COMMENT ON COLUMN "auditlog"."user_id" IS '用户ID';
COMMENT ON COLUMN "auditlog"."username" IS '用户名称';
COMMENT ON COLUMN "auditlog"."module" IS '功能模块';
COMMENT ON COLUMN "auditlog"."summary" IS '请求描述';
COMMENT ON COLUMN "auditlog"."method" IS '请求方法';
COMMENT ON COLUMN "auditlog"."path" IS '请求路径';
COMMENT ON COLUMN "auditlog"."status" IS '状态码';
COMMENT ON COLUMN "auditlog"."response_time" IS '响应时间(单位ms)';
COMMENT ON COLUMN "auditlog"."request_args" IS '请求参数';
COMMENT ON COLUMN "auditlog"."response_body" IS '返回数据';
CREATE TABLE "dept" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL UNIQUE,
    "desc" VARCHAR(500),
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "order" INT NOT NULL  DEFAULT 0,
    "parent_id" INT NOT NULL  DEFAULT 0
);
CREATE INDEX "idx_dept_created_4b11cf" ON "dept" ("created_at");
CREATE INDEX "idx_dept_updated_0c0bd1" ON "dept" ("updated_at");
CREATE INDEX "idx_dept_name_c2b9da" ON "dept" ("name");
CREATE INDEX "idx_dept_is_dele_466228" ON "dept" ("is_deleted");
CREATE INDEX "idx_dept_order_ddabe1" ON "dept" ("order");
CREATE INDEX "idx_dept_parent__a71a57" ON "dept" ("parent_id");
COMMENT ON COLUMN "dept"."name" IS '部门名称';
COMMENT ON COLUMN "dept"."desc" IS '备注';
COMMENT ON COLUMN "dept"."is_deleted" IS '软删除标记';
COMMENT ON COLUMN "dept"."order" IS '排序';
COMMENT ON COLUMN "dept"."parent_id" IS '父部门ID';
CREATE TABLE "deptclosure" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "ancestor" INT NOT NULL,
    "descendant" INT NOT NULL,
    "level" INT NOT NULL  DEFAULT 0
);
CREATE INDEX "idx_deptclosure_created_96f6ef" ON "deptclosure" ("created_at");
CREATE INDEX "idx_deptclosure_updated_41fc08" ON "deptclosure" ("updated_at");
CREATE INDEX "idx_deptclosure_ancesto_fbc4ce" ON "deptclosure" ("ancestor");
CREATE INDEX "idx_deptclosure_descend_2ae8b1" ON "deptclosure" ("descendant");
CREATE INDEX "idx_deptclosure_level_ae16b2" ON "deptclosure" ("level");
COMMENT ON COLUMN "deptclosure"."ancestor" IS '父代';
COMMENT ON COLUMN "deptclosure"."descendant" IS '子代';
COMMENT ON COLUMN "deptclosure"."level" IS '深度';
CREATE TABLE "menu" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL,
    "remark" JSONB,
    "menu_type" VARCHAR(7),
    "icon" VARCHAR(100),
    "path" VARCHAR(100) NOT NULL,
    "order" INT NOT NULL  DEFAULT 0,
    "parent_id" INT NOT NULL  DEFAULT 0,
    "is_hidden" BOOL NOT NULL  DEFAULT False,
    "component" VARCHAR(100) NOT NULL,
    "keepalive" BOOL NOT NULL  DEFAULT True,
    "redirect" VARCHAR(100)
);
CREATE INDEX "idx_menu_created_b6922b" ON "menu" ("created_at");
CREATE INDEX "idx_menu_updated_e6b0a1" ON "menu" ("updated_at");
CREATE INDEX "idx_menu_name_b9b853" ON "menu" ("name");
CREATE INDEX "idx_menu_path_bf95b2" ON "menu" ("path");
CREATE INDEX "idx_menu_order_606068" ON "menu" ("order");
CREATE INDEX "idx_menu_parent__bebd15" ON "menu" ("parent_id");
COMMENT ON COLUMN "menu"."name" IS '菜单名称';
COMMENT ON COLUMN "menu"."remark" IS '保留字段';
COMMENT ON COLUMN "menu"."menu_type" IS '菜单类型';
COMMENT ON COLUMN "menu"."icon" IS '菜单图标';
COMMENT ON COLUMN "menu"."path" IS '菜单路径';
COMMENT ON COLUMN "menu"."order" IS '排序';
COMMENT ON COLUMN "menu"."parent_id" IS '父菜单ID';
COMMENT ON COLUMN "menu"."is_hidden" IS '是否隐藏';
COMMENT ON COLUMN "menu"."component" IS '组件';
COMMENT ON COLUMN "menu"."keepalive" IS '存活';
COMMENT ON COLUMN "menu"."redirect" IS '重定向';
CREATE TABLE "role" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL UNIQUE,
    "desc" VARCHAR(500)
);
CREATE INDEX "idx_role_created_7f5f71" ON "role" ("created_at");
CREATE INDEX "idx_role_updated_5dd337" ON "role" ("updated_at");
CREATE INDEX "idx_role_name_e5618b" ON "role" ("name");
COMMENT ON COLUMN "role"."name" IS '角色名称';
COMMENT ON COLUMN "role"."desc" IS '角色描述';
CREATE TABLE "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "sub" VARCHAR(32) NOT NULL UNIQUE,
    "username" VARCHAR(20) NOT NULL UNIQUE,
    "alias" VARCHAR(30),
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "phone" VARCHAR(20),
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_superuser" BOOL NOT NULL  DEFAULT False,
    "last_login" TIMESTAMPTZ,
    "dept_id" INT
);
CREATE INDEX "idx_user_created_b19d59" ON "user" ("created_at");
CREATE INDEX "idx_user_updated_dfdb43" ON "user" ("updated_at");
CREATE INDEX "idx_user_sub_bc4465" ON "user" ("sub");
CREATE INDEX "idx_user_usernam_9987ab" ON "user" ("username");
CREATE INDEX "idx_user_alias_6f9868" ON "user" ("alias");
CREATE INDEX "idx_user_email_1b4f1c" ON "user" ("email");
CREATE INDEX "idx_user_phone_4e3ecc" ON "user" ("phone");
CREATE INDEX "idx_user_is_acti_83722a" ON "user" ("is_active");
CREATE INDEX "idx_user_is_supe_b8a218" ON "user" ("is_superuser");
CREATE INDEX "idx_user_last_lo_af118a" ON "user" ("last_login");
CREATE INDEX "idx_user_dept_id_d4490b" ON "user" ("dept_id");
COMMENT ON COLUMN "user"."sub" IS '身份账号 sub';
COMMENT ON COLUMN "user"."username" IS '用户名称';
COMMENT ON COLUMN "user"."alias" IS '姓名';
COMMENT ON COLUMN "user"."email" IS '邮箱';
COMMENT ON COLUMN "user"."phone" IS '电话';
COMMENT ON COLUMN "user"."is_active" IS '是否激活';
COMMENT ON COLUMN "user"."is_superuser" IS '是否为超级管理员';
COMMENT ON COLUMN "user"."last_login" IS '最后登录时间';
COMMENT ON COLUMN "user"."dept_id" IS '部门ID';
COMMENT ON TABLE "user" IS '控制台本地用户：按 sub 关联认证模块的身份账号，用户名、邮箱为本地资料副本';
CREATE TABLE "role_api" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "api_id" BIGINT NOT NULL REFERENCES "api" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_role_api_role_id_ba4286" ON "role_api" ("role_id", "api_id");
CREATE TABLE "role_menu" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "menu_id" BIGINT NOT NULL REFERENCES "menu" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_role_menu_role_id_90801c" ON "role_menu" ("role_id", "menu_id");
CREATE TABLE "user_role" (
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_user_role_user_id_d0bad3" ON "user_role" ("user_id", "role_id");
"""

TABLES = ["user_role", "role_api", "role_menu", "user", "role", "menu", "deptclosure", "dept", "auditlog", "api"]


def upgrade() -> None:
    # pgvector 供后续知识库 / 能力模块使用（docs/overview.md：PostgreSQL + pgvector）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
