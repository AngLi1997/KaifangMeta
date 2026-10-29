"""机构管理：iam.org、身份账号所属机构、菜单与接口权限

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-29
"""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

# 租户管理员维护本租户机构，与身份账号一致
APIS = [
    ("GET", "/org/tree", "查看机构树", "机构"),
    ("POST", "/org/create", "新增机构", "机构"),
    ("POST", "/org/update", "修改机构", "机构"),
    ("DELETE", "/org/delete", "删除机构", "机构"),
    ("POST", "/org/import", "导入机构", "机构"),
]
ROLES = ["管理员", "租户管理员"]


def upgrade() -> None:
    from app.settings.config import settings

    op.execute(
        """CREATE TABLE iam."org" (
            "id" BIGSERIAL PRIMARY KEY,
            "tenant_id" VARCHAR(32) NOT NULL,
            "parent_id" BIGINT,
            "code" VARCHAR(64) NOT NULL,
            "name" VARCHAR(128) NOT NULL,
            "sort_order" INT NOT NULL DEFAULT 0,
            "status" VARCHAR(16) NOT NULL DEFAULT 'active',
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "uid_org_tenant_code" UNIQUE ("tenant_id", "code")
        );
        CREATE INDEX "idx_org_tenant" ON iam."org" ("tenant_id");
        CREATE INDEX "idx_org_parent" ON iam."org" ("parent_id");
        COMMENT ON TABLE iam."org" IS '机构：按租户维护的机构树';
        ALTER TABLE iam."account" ADD COLUMN "org_id" BIGINT;
        CREATE INDEX "idx_account_org" ON iam."account" ("org_id");"""
    )
    system = settings.IAM_SYSTEM_TENANT.replace("'", "''")
    # RLS 兜底与 0013 一致：未设置租户或系统租户可见全部
    op.execute(
        f"""ALTER TABLE iam."org" ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam."org" USING (
            coalesce(current_setting('app.tenant_id', true), '') IN ('', '{system}')
            OR tenant_id = current_setting('app.tenant_id', true));"""
    )

    conn = op.get_bind()
    system_id = conn.execute(sa.text('SELECT id FROM "menu" WHERE path = \'/system\'')).scalar_one()
    conn.execute(
        sa.text('UPDATE "menu" SET "order" = "order" + 1 WHERE parent_id = :pid AND "order" >= 2'),
        {"pid": system_id},
    )
    menu_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
               VALUES ('menu', '机构管理', 'org', 2, :pid, 'icon-park-outline:tree-diagram', false, '/system/org', false)
               RETURNING id"""
        ),
        {"pid": system_id},
    ).scalar_one()
    conn.execute(
        sa.text(
            'INSERT INTO "role_menu" (role_id, menu_id) SELECT id, :mid FROM "role" WHERE name = ANY(:roles) '
            "ON CONFLICT DO NOTHING"
        ),
        {"mid": menu_id, "roles": ROLES},
    )
    for method, suffix, summary, tags in APIS:
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
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a
                   WHERE r.name = ANY(:roles) AND a.method = :method AND a.path = :path
                   ON CONFLICT DO NOTHING"""
            ),
            {"method": method, "path": path, "roles": ROLES},
        )


def downgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    for method, suffix, *_ in APIS:
        conn.execute(
            sa.text('DELETE FROM "api" WHERE method = :method AND path = :path'),
            {"method": method, "path": f"{settings.API_PREFIX}/v1{suffix}"},
        )
    conn.execute(sa.text('DELETE FROM "menu" WHERE path = \'org\' AND component = \'/system/org\''))
    conn.execute(
        sa.text(
            'UPDATE "menu" SET "order" = "order" - 1 WHERE parent_id = '
            '(SELECT id FROM "menu" WHERE path = \'/system\') AND "order" >= 3'
        )
    )
    op.execute(
        """ALTER TABLE iam."account" DROP COLUMN "org_id";
        DROP TABLE iam."org";"""
    )
