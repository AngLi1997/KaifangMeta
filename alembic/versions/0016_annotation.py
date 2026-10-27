"""数据标注模块：annotation schema（场景模板、工单、条目）、内置场景模板、菜单与接口权限

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

SCHEMA_SQL = """
CREATE TABLE "template" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tenant_id" VARCHAR(32) NOT NULL,
    "scope" VARCHAR(16) NOT NULL DEFAULT 'tenant',
    "code" VARCHAR(64) NOT NULL,
    "name" VARCHAR(64) NOT NULL,
    "modality" VARCHAR(16) NOT NULL,
    "config" TEXT NOT NULL,
    "version" INT NOT NULL DEFAULT 1,
    "created_by" VARCHAR(32) NOT NULL DEFAULT '',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("tenant_id", "code")
);
CREATE INDEX "idx_template_tenant" ON "template" ("tenant_id");
COMMENT ON TABLE "template" IS '场景模板：Label Studio 模板 XML，修改时 version + 1';

CREATE TABLE "task" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tenant_id" VARCHAR(32) NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "mode" VARCHAR(16) NOT NULL DEFAULT 'assigned',
    "template_id" BIGINT NOT NULL,
    "template_name" VARCHAR(64) NOT NULL,
    "template_ref" VARCHAR(80) NOT NULL,
    "config" TEXT NOT NULL,
    "status" VARCHAR(16) NOT NULL DEFAULT 'CREATED',
    "item_count" INT NOT NULL DEFAULT 0,
    "labeled_count" INT NOT NULL DEFAULT 0,
    "created_by" VARCHAR(32) NOT NULL DEFAULT '',
    "creator_name" VARCHAR(64) NOT NULL DEFAULT '',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_task_tenant" ON "task" ("tenant_id");
CREATE INDEX "idx_task_status" ON "task" ("status");
CREATE INDEX "idx_task_created_at" ON "task" ("created_at");
COMMENT ON TABLE "task" IS '标注工单；config 为建单时的模板 XML 快照';

CREATE TABLE "item" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tenant_id" VARCHAR(32) NOT NULL,
    "task_id" BIGINT NOT NULL REFERENCES "task" ("id") ON DELETE CASCADE,
    "item_key" VARCHAR(64) NOT NULL,
    "name" VARCHAR(255) NOT NULL DEFAULT '',
    "file" VARCHAR(500) NOT NULL DEFAULT '',
    "data" JSONB NOT NULL DEFAULT '{}',
    "status" VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    "result" JSONB,
    "annotated_by" VARCHAR(32) NOT NULL DEFAULT '',
    "annotator_name" VARCHAR(64) NOT NULL DEFAULT '',
    "annotated_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("task_id", "item_key")
);
CREATE INDEX "idx_item_tenant" ON "item" ("tenant_id");
CREATE INDEX "idx_item_task_status" ON "item" ("task_id", "status");
COMMENT ON TABLE "item" IS '标注条目；result 为最新提交的 Label Studio 结果';
"""

# 内置场景模板（系统模板，所有租户可见）：编码、名称、模态、模板 XML
SYSTEM_TEMPLATES = [
    (
        "image.bbox",
        "图像目标检测",
        "image",
        """<View>
  <Image name="image" value="$image" zoom="true"/>
  <RectangleLabels name="label" toName="image">
    <Label value="印章" background="#d03050"/>
    <Label value="签名" background="#2080f0"/>
    <Label value="标题" background="#18a058"/>
    <Label value="表格" background="#f0a020"/>
  </RectangleLabels>
</View>""",
    ),
    (
        "image.classify",
        "图像分类",
        "image",
        """<View>
  <Image name="image" value="$image"/>
  <Choices name="category" toName="image" choice="single" showInline="true">
    <Choice value="文书"/>
    <Choice value="照片"/>
    <Choice value="图纸"/>
    <Choice value="其他"/>
  </Choices>
</View>""",
    ),
    (
        "ocr.proofread",
        "OCR 文本校对",
        "document",
        """<View>
  <Image name="image" value="$image" zoom="true"/>
  <Rectangle name="bbox" toName="image" strokeWidth="2"/>
  <TextArea name="transcription" toName="image" editable="true" perRegion="true" placeholder="识别文字"/>
</View>""",
    ),
    (
        "archive.ws-item",
        "文书著录要素校对",
        "document",
        """<View>
  <Image name="image" value="$image" zoom="true"/>
  <Header value="题名"/>
  <TextArea name="title" toName="image" editable="true" maxSubmissions="1"/>
  <Header value="文号"/>
  <TextArea name="doc_no" toName="image" editable="true" maxSubmissions="1"/>
  <Header value="责任者"/>
  <TextArea name="author" toName="image" editable="true" maxSubmissions="1"/>
  <Header value="密级"/>
  <Choices name="secret" toName="image" choice="single" showInline="true">
    <Choice value="公开"/>
    <Choice value="内部"/>
    <Choice value="秘密"/>
  </Choices>
</View>""",
    ),
    (
        "text.classify",
        "文本分类",
        "text",
        """<View>
  <Text name="text" value="$text"/>
  <Choices name="category" toName="text" choice="single" showInline="true">
    <Choice value="通知"/>
    <Choice value="请示"/>
    <Choice value="报告"/>
    <Choice value="函"/>
  </Choices>
</View>""",
    ),
    (
        "text.ner",
        "命名实体识别",
        "text",
        """<View>
  <Labels name="label" toName="text">
    <Label value="人名" background="#d03050"/>
    <Label value="机构" background="#2080f0"/>
    <Label value="地点" background="#18a058"/>
    <Label value="日期" background="#f0a020"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>""",
    ),
]

API_PREFIX_SUFFIXES = [
    ("GET", "/annotation/template/list", "查看场景模板列表"),
    ("POST", "/annotation/template/create", "新建场景模板"),
    ("POST", "/annotation/template/update", "修改场景模板"),
    ("GET", "/annotation/task/list", "查看标注工单列表"),
    ("GET", "/annotation/task/get", "查看标注工单"),
    ("POST", "/annotation/task/create", "新建标注工单"),
    ("POST", "/annotation/task/upload", "上传标注数据"),
    ("GET", "/annotation/item/list", "查看标注条目列表"),
    ("GET", "/annotation/item/get", "查看标注条目"),
    ("POST", "/annotation/item/save", "提交标注结果"),
]

# 未设置 app.tenant_id 或处于系统租户时不限制（同 0013）
TENANT_VISIBLE = "coalesce(current_setting('app.tenant_id', true), '') IN ('', '{system}')"
CURRENT = "current_setting('app.tenant_id', true)"


def upgrade() -> None:
    from app.settings.config import settings

    conn = op.get_bind()
    schema = settings.ANNOTATION_SCHEMA
    system = settings.IAM_SYSTEM_TENANT

    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    op.execute(f'SET LOCAL search_path TO "{schema}"')
    op.execute(SCHEMA_SQL)
    for code, name, modality, config in SYSTEM_TEMPLATES:
        conn.execute(
            sa.text(
                """INSERT INTO "template" (tenant_id, scope, code, name, modality, config)
                   VALUES (:tid, 'system', :code, :name, :modality, :config)"""
            ),
            {"tid": system, "code": code, "name": name, "modality": modality, "config": config},
        )

    # RLS 兜底；系统模板对所有租户只读可见
    visible = TENANT_VISIBLE.format(system=system.replace("'", "''"))
    for table, extra in [("template", " OR scope = 'system'"), ("task", ""), ("item", "")]:
        op.execute(
            f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;'
            f'CREATE POLICY tenant_isolation ON "{table}" USING ({visible} OR tenant_id = {CURRENT}{extra});'
        )

    user = settings.POSTGRES_APP_USER.replace('"', '""')
    op.execute(
        f"""GRANT USAGE ON SCHEMA "{schema}" TO "{user}";
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{user}";
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA "{schema}" TO "{user}";"""
    )
    op.execute("SET LOCAL search_path TO console_authz, public")

    # ---- 菜单：数据标注 → 标注工单、场景模板；工单详情与标注工作台为隐藏菜单 ----
    op.execute("""UPDATE "menu" SET "order" = 3 WHERE path = '/ops' AND menu_type = 'catalog'""")
    root_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive, redirect)
               VALUES ('catalog', '数据标注', '/annotation', 2, 0, 'icon-park-outline:label', false, 'Layout', false, '/annotation/task')
               RETURNING id"""
        )
    ).scalar_one()
    menu_ids = [root_id]
    for name, path, order, icon, hidden in [
        ("标注工单", "task", 1, "icon-park-outline:list-checkbox", False),
        ("场景模板", "template", 2, "icon-park-outline:page-template", False),
        ("工单详情", "task-detail", 3, "icon-park-outline:file-search", True),
        ("标注工作台", "workbench", 4, "icon-park-outline:edit-two", True),
    ]:
        menu_ids.append(
            conn.execute(
                sa.text(
                    """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
                       VALUES ('menu', :name, :path, :order, :pid, :icon, :hidden, :component, false)
                       RETURNING id"""
                ),
                {
                    "name": name,
                    "path": path,
                    "order": order,
                    "pid": root_id,
                    "icon": icon,
                    "hidden": hidden,
                    "component": f"/annotation/{path}",
                },
            ).scalar_one()
        )

    # ---- 接口登记，并授予管理员与租户管理员 ----
    for method, suffix, summary in API_PREFIX_SUFFIXES:
        conn.execute(
            sa.text(
                """INSERT INTO "api" (method, path, summary, tags)
                   SELECT CAST(:method AS varchar), CAST(:path AS varchar), CAST(:summary AS varchar), '数据标注'
                   WHERE NOT EXISTS (SELECT 1 FROM "api" WHERE method = :method AND path = :path)"""
            ),
            {"method": method, "path": f"{settings.API_PREFIX}/v1{suffix}", "summary": summary},
        )
    for role in ["管理员", "租户管理员"]:
        for menu_id in menu_ids:
            conn.execute(
                sa.text(
                    'INSERT INTO "role_menu" (role_id, menu_id) '
                    'SELECT id, :menu_id FROM "role" WHERE name = :role ON CONFLICT DO NOTHING'
                ),
                {"menu_id": menu_id, "role": role},
            )
        conn.execute(
            sa.text(
                """INSERT INTO "role_api" (role_id, api_id)
                   SELECT r.id, a.id FROM "role" r CROSS JOIN "api" a
                   WHERE r.name = :role AND a.path LIKE :prefix ON CONFLICT DO NOTHING"""
            ),
            {"role": role, "prefix": f"{settings.API_PREFIX}/v1/annotation/%"},
        )


def downgrade() -> None:
    from app.settings.config import settings

    op.execute(f"""DELETE FROM "api" WHERE path LIKE '{settings.API_PREFIX}/v1/annotation/%'""")
    op.execute(
        'DELETE FROM "menu" WHERE parent_id = '
        '(SELECT id FROM "menu" WHERE path = \'/annotation\' AND menu_type = \'catalog\') OR path = \'/annotation\''
    )
    op.execute("""UPDATE "menu" SET "order" = 2 WHERE path = '/ops' AND menu_type = 'catalog'""")
    op.execute(f'DROP SCHEMA IF EXISTS "{settings.ANNOTATION_SCHEMA}" CASCADE')
