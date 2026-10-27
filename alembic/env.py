from logging.config import fileConfig

from sqlalchemy import create_engine, text

from alembic import context
from app.settings.config import settings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

SCHEMA = settings.POSTGRES_SCHEMA
# 平台单一迁移链，版本表放 public；各模块迁移只操作本模块 schema
VERSION_SCHEMA = "public"


def run_migrations_offline() -> None:
    context.configure(url=settings.DATABASE_URL, literal_binds=True, version_table_schema=VERSION_SCHEMA)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as connection:
        # 每个平台模块独立 schema，迁移只作用于本模块 schema
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.execute(text(f'SET search_path TO "{SCHEMA}", public'))
        connection.commit()
        context.configure(connection=connection, version_table_schema=VERSION_SCHEMA)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
