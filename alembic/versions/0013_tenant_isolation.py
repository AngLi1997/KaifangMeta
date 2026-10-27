"""租户级隔离：系统租户、跨租户成员、角色作用范围与绑定、审计租户、运行时账号与 RLS

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

TENANT_ADMIN = "租户管理员"
TENANT_ADMIN_APIS = [
    ("GET", "/base/userinfo", "查看用户信息", "基础模块"),
    ("GET", "/base/usermenu", "查看用户菜单", "基础模块"),
    ("GET", "/base/userapi", "查看用户API", "基础模块"),
    ("POST", "/base/update_password", "修改密码", "基础模块"),
    ("POST", "/base/avatar", "上传用户头像", "基础模块"),
    ("GET", "/account/list", "查看身份账号列表", "身份账号"),
    ("POST", "/account/create", "新建身份账号", "身份账号"),
    ("POST", "/account/update", "修改身份账号", "身份账号"),
    ("GET", "/user/list", "读取身份账号对应的控制台授权信息", "身份账号关联信息"),
    ("POST", "/user/roles", "设置控制台角色", "身份账号关联信息"),
    ("GET", "/role/list", "查看角色列表", "角色管理"),
    ("GET", "/tenant/list", "查看租户列表", "租户"),
    ("GET", "/auditlog/list", "查看操作日志", "审计日志模块"),
]

# 未设置 app.tenant_id（认证流程、worker、迁移）或处于系统租户时不限制；控制台请求在事务内 SET LOCAL app.tenant_id / app.sub
TENANT_VISIBLE = "coalesce(current_setting('app.tenant_id', true), '') IN ('', '{system}')"
CURRENT = "current_setting('app.tenant_id', true)"


def _policy(table: str, system: str, extra: str = "") -> str:
    visible = TENANT_VISIBLE.format(system=system.replace("'", "''"))
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
        f"CREATE POLICY tenant_isolation ON {table} USING ({visible} OR tenant_id = {CURRENT}{extra});"
    )


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    system = settings.IAM_SYSTEM_TENANT

    # ---- 认证模块：系统租户、超级管理员归属、跨租户成员、控制台对全部租户开通 ----
    conn.execute(
        sa.text(
            "INSERT INTO iam.tenant (id, name, status) VALUES (:id, '系统租户', 'active') ON CONFLICT (id) DO NOTHING"
        ),
        {"id": system},
    )
    conn.execute(
        sa.text(
            'UPDATE iam.account SET tenant_id = :id WHERE sub IN (SELECT sub FROM "user" WHERE is_superuser)'
        ),
        {"id": system},
    )
    op.execute(
        """CREATE TABLE iam."tenant_member" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "sub" VARCHAR(32) NOT NULL,
            "tenant_id" VARCHAR(32) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE ("sub", "tenant_id")
        );
        CREATE INDEX "idx_tenant_member_tenant" ON iam."tenant_member" ("tenant_id");
        COMMENT ON TABLE iam."tenant_member" IS '跨租户成员：账号在主租户之外可登录的租户'"""
    )
    conn.execute(
        sa.text(
            "UPDATE iam.client SET tenants = (SELECT jsonb_agg(id ORDER BY created_at) FROM iam.tenant) "
            "WHERE client_id = :cid"
        ),
        {"cid": settings.CONSOLE_CLIENT_ID},
    )

    # ---- 控制台：成员资料放宽到 IAM 字段长度，角色作用范围，按租户的角色绑定，审计租户 ----
    op.execute(
        """ALTER TABLE "user" ALTER COLUMN "username" TYPE VARCHAR(64), ALTER COLUMN "email" DROP NOT NULL;
        ALTER TABLE "role" ADD COLUMN "scope" VARCHAR(16) NOT NULL DEFAULT 'tenant';
        COMMENT ON COLUMN "role"."scope" IS '作用范围：system 仅在系统租户生效，tenant 在绑定的租户内生效';
        UPDATE "role" SET "scope" = 'system' WHERE "name" = '管理员';
        CREATE TABLE "role_binding" (
            "id" BIGSERIAL NOT NULL PRIMARY KEY,
            "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
            "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
            "tenant_id" VARCHAR(32) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE ("user_id", "role_id", "tenant_id")
        );
        CREATE INDEX "idx_role_binding_tenant" ON "role_binding" ("tenant_id");
        COMMENT ON TABLE "role_binding" IS '角色绑定：成员 × 角色 × 租户，只在 Token 的租户内生效';
        INSERT INTO "role_binding" ("user_id", "role_id", "tenant_id")
            SELECT ur.user_id, ur.role_id, a.tenant_id FROM "user_role" ur
            JOIN "user" u ON u.id = ur.user_id JOIN iam.account a ON a.sub = u.sub;
        DROP TABLE "user_role";
        ALTER TABLE "auditlog" ADD COLUMN "tenant_id" VARCHAR(32) NOT NULL DEFAULT '';
        CREATE INDEX "idx_auditlog_tenant" ON "auditlog" ("tenant_id");"""
    )

    # ---- 内置租户管理员：管理本租户账号、控制台角色，查看本租户审计 ----
    role_id = conn.execute(
        sa.text(
            """INSERT INTO "role" (name, "desc", scope) VALUES (:name, '管理本租户的身份账号与控制台角色', 'tenant')
               ON CONFLICT (name) DO UPDATE SET scope = 'tenant' RETURNING id"""
        ),
        {"name": TENANT_ADMIN},
    ).scalar_one()
    conn.execute(
        sa.text(
            """INSERT INTO "role_menu" (role_id, menu_id)
               SELECT :rid, id FROM "menu" WHERE path IN ('/system', 'account', 'auditlog') ON CONFLICT DO NOTHING"""
        ),
        {"rid": role_id},
    )
    for method, suffix, summary, tags in TENANT_ADMIN_APIS:
        path = f"{settings.API_PREFIX}/v1{suffix}"
        conn.execute(
            sa.text(
                """INSERT INTO "api" (method, path, summary, tags)
                   SELECT CAST(:method AS varchar), CAST(:path AS varchar), CAST(:summary AS varchar), CAST(:tags AS varchar)
                   WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = :method AND path = :path)"""
            ),
            {"method": method, "path": path, "summary": summary, "tags": tags},
        )
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT :rid, id FROM "api" WHERE method = :method AND path = :path ON CONFLICT DO NOTHING"""
            ),
            {"rid": role_id, "method": method, "path": path},
        )
    # 管理员是系统角色，不再依赖超管绕过权限校验：授予全部现有接口（含此前漏授的 /account/list）
    op.execute(
        """INSERT INTO "role_api" (role_id, api_id)
           SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a WHERE r.name = '管理员' ON CONFLICT DO NOTHING"""
    )

    # ---- RLS 兜底：带 tenant_id 的表按 app.tenant_id 过滤 ----
    member = f" OR EXISTS (SELECT 1 FROM iam.tenant_member m WHERE m.sub = account.sub AND m.tenant_id = {CURRENT})"
    for table, extra in [
        ("iam.account", member),
        # 本人的成员关系始终可见：userinfo 列出可切换的租户
        ("iam.tenant_member", " OR sub = current_setting('app.sub', true)"),
        ('"role_binding"', ""),
        ('"auditlog"', ""),
    ]:
        op.execute(_policy(table, system, extra))

    # ---- 运行时账号：非超级用户、不绕过 RLS；后续迁移新建的表自动授权 ----
    user = settings.POSTGRES_APP_USER.replace('"', '""')
    password = settings.POSTGRES_APP_PASSWORD.replace("'", "''")
    db = settings.POSTGRES_DB.replace('"', '""')
    op.execute(
        f"""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{user.replace("'", "''")}') THEN
                CREATE ROLE "{user}" LOGIN;
            END IF;
        END $$;
        ALTER ROLE "{user}" WITH LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
        GRANT CONNECT ON DATABASE "{db}" TO "{user}";
        GRANT USAGE ON SCHEMA console_authz, iam TO "{user}";
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA console_authz, iam TO "{user}";
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA console_authz, iam TO "{user}";
        ALTER DEFAULT PRIVILEGES IN SCHEMA console_authz, iam
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{user}";
        ALTER DEFAULT PRIVILEGES IN SCHEMA console_authz, iam GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO "{user}";"""
    )


def downgrade() -> None:
    for table in ["iam.account", "iam.tenant_member", '"role_binding"', '"auditlog"']:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE TABLE "user_role" (
            "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
            "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX "uidx_user_role_user_id_d0bad3" ON "user_role" ("user_id", "role_id");
        INSERT INTO "user_role" SELECT DISTINCT user_id, role_id FROM "role_binding";
        DROP TABLE "role_binding";
        DELETE FROM "role" WHERE name = '租户管理员';
        ALTER TABLE "role" DROP COLUMN "scope";
        ALTER TABLE "auditlog" DROP COLUMN "tenant_id";
        DROP TABLE iam."tenant_member";"""
    )
    # 系统租户由 0003 初始化，回滚不删除；运行时账号与默认权限保留，回滚后改回 POSTGRES_USER 连接即可
