"""Rename ETCD menu and set its database network icon

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-27
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        '''UPDATE "menu" SET name = 'ETCD', icon = 'icon-park-outline:database-network'
           WHERE menu_type = 'menu' AND path = 'etcd'
             AND parent_id = (SELECT id FROM "menu" WHERE menu_type = 'catalog' AND path = '/ops')'''
    )


def downgrade() -> None:
    op.execute(
        '''UPDATE "menu" SET name = 'etcd', icon = 'icon-park-outline:database'
           WHERE menu_type = 'menu' AND path = 'etcd'
             AND parent_id = (SELECT id FROM "menu" WHERE menu_type = 'catalog' AND path = '/ops')'''
    )
