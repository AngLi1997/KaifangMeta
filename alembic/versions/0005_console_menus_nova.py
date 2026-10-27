"""控制台菜单：新增「身份账号」，移除上游演示菜单，图标统一为 nova-admin 的 icon-park-outline

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# path → (新图标, 旧图标)
ICONS = {
    "/system": ("icon-park-outline:setting-two", "carbon:gui-management"),
    "user": ("icon-park-outline:every-user", "material-symbols:person-outline-rounded"),
    "role": ("icon-park-outline:permissions", "carbon:user-role"),
    "menu": ("icon-park-outline:hamburger-button", "material-symbols:list-alt-outline"),
    "api": ("icon-park-outline:api", "ant-design:api-outlined"),
    "dept": ("icon-park-outline:tree-diagram", "mingcute:department-line"),
    "auditlog": ("icon-park-outline:log", "ph:clipboard-text-bold"),
}


def upgrade() -> None:
    conn = op.get_bind()
    for path, (new, _) in ICONS.items():
        conn.execute(sa.text('UPDATE "menu" SET icon = :icon WHERE path = :path'), dict(icon=new, path=path))
    conn.execute(sa.text("DELETE FROM \"menu\" WHERE path = '/top-menu'"))

    system_id = conn.execute(sa.text("SELECT id FROM \"menu\" WHERE path = '/system'")).scalar_one()
    account_id = conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive)
               VALUES ('menu', '身份账号', 'account', 1, :pid, 'icon-park-outline:id-card', false, '/system/account', false)
               RETURNING id"""
        ),
        dict(pid=system_id),
    ).scalar_one()
    # 只授权给管理员角色；接口权限由启动时同步的 API 清单在角色中配置
    conn.execute(
        sa.text('INSERT INTO "role_menu" (role_id, menu_id) SELECT id, :mid FROM "role" WHERE name = \'管理员\''),
        dict(mid=account_id),
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM \"menu\" WHERE path = 'account' AND component = '/system/account'"))
    for path, (_, old) in ICONS.items():
        conn.execute(sa.text('UPDATE "menu" SET icon = :icon WHERE path = :path'), dict(icon=old, path=path))
    conn.execute(
        sa.text(
            """INSERT INTO "menu" (menu_type, name, path, "order", parent_id, icon, is_hidden, component, keepalive, redirect)
               VALUES ('menu', '一级菜单', '/top-menu', 2, 0, 'material-symbols:featured-play-list-outline', false,
                       '/top-menu', false, '')"""
        )
    )
