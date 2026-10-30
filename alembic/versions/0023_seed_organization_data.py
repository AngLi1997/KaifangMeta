"""同步底座机构快照，清理演示机构并合并重复编码节点

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-29
"""

import json
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

DEMO_ORGS = [
    (100, "37", "示例省"),
    (104, "3701", "示例市"),
    (105, "370102", "示例区"),
    (106, "3702", "示例二市"),
    (107, "370202", "示例二区"),
]


def upgrade() -> None:
    from app.settings.config import settings

    tenant_id = settings.IAM_SYSTEM_TENANT
    snapshot = json.loads(Path(__file__).with_name("0023_organization_seed.json").read_text(encoding="utf-8"))
    rows = snapshot["organizations"]
    id_map = {int(source_id): target_id for source_id, target_id in snapshot["collapsed_source_id_map"].items()}
    ids = [row["id"] for row in rows]
    codes = [row["code"] for row in rows]
    by_id = {row["id"]: row for row in rows}

    if len(rows) != 615 or len(id_map) != 22 or 100 in by_id:
        raise RuntimeError("机构快照数量或演示数据排除项不正确")
    if any(source_id in by_id or target_id not in by_id for source_id, target_id in id_map.items()):
        raise RuntimeError("机构快照重复编码映射不完整")
    if len(ids) != len(set(ids)) or len(codes) != len(set(codes)):
        raise RuntimeError("机构快照存在重复 ID 或编码")
    if any(row["parent_id"] is not None and row["parent_id"] not in by_id for row in rows):
        raise RuntimeError("机构快照包含不存在的上级机构")
    for row in rows:
        seen = {row["id"]}
        parent_id = row["parent_id"]
        while parent_id is not None:
            if parent_id in seen:
                raise RuntimeError("机构快照存在上下级循环")
            seen.add(parent_id)
            parent_id = by_id[parent_id]["parent_id"]

    conn = op.get_bind()
    for org_id, code, name in DEMO_ORGS:
        deleted_id = conn.execute(
            sa.text(
                'DELETE FROM iam."org" WHERE id = :id AND tenant_id = :tenant_id '
                'AND code = :code AND name = :name RETURNING id'
            ),
            {"id": org_id, "tenant_id": tenant_id, "code": code, "name": name},
        ).scalar_one_or_none()
        if deleted_id is not None:
            conn.execute(
                sa.text('UPDATE iam."account" SET org_id = NULL WHERE tenant_id = :tenant_id AND org_id = :org_id'),
                {"tenant_id": tenant_id, "org_id": deleted_id},
            )

    for source_id, target_id in id_map.items():
        conn.execute(
            sa.text(
                'UPDATE iam."account" SET org_id = :target_id '
                'WHERE tenant_id = :tenant_id AND org_id = :source_id'
            ),
            {"tenant_id": tenant_id, "source_id": source_id, "target_id": target_id},
        )

    id_conflicts = conn.execute(
        sa.text('SELECT id FROM iam."org" WHERE id IN :ids').bindparams(sa.bindparam("ids", expanding=True)),
        {"ids": ids},
    ).scalars().all()
    code_conflicts = conn.execute(
        sa.text('SELECT code FROM iam."org" WHERE tenant_id = :tenant_id AND code IN :codes').bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"tenant_id": tenant_id, "codes": codes},
    ).scalars().all()
    if id_conflicts or code_conflicts:
        raise RuntimeError("机构快照与已有机构冲突；未覆盖已有数据")

    conn.execute(
        sa.text(
            'INSERT INTO iam."org" (id, tenant_id, parent_id, code, name, sort_order, status) '
            'VALUES (:id, :tenant_id, :parent_id, :code, :name, 0, \'active\')'
        ),
        [{**row, "tenant_id": tenant_id} for row in rows],
    )
    conn.execute(
        sa.text("SELECT setval(pg_get_serial_sequence('iam.org', 'id'), GREATEST((SELECT max(id) FROM iam.org), 1))")
    )
    conn.execute(
        sa.text(
            'INSERT INTO iam."outbox" (type, subject, tenant_id, data) '
            "VALUES ('org.changed', 'import', :tenant_id, CAST(:data AS jsonb))"
        ),
        {"tenant_id": tenant_id, "data": json.dumps({"tenant_id": tenant_id, "org_id": None})},
    )


def downgrade() -> None:
    # shortcut: 22 source IDs were merged and demo links cleared; add a reverse map before enabling rollback.
    raise RuntimeError("机构数据快照无法安全自动回滚")
