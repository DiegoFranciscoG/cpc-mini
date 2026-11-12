"""Entorno de Alembic: la URL viene de CPCMINI_DATABASE_URL (o de config.attributes en pruebas)."""

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from cpcmini.db.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("database_url") or os.environ.get("CPCMINI_DATABASE_URL")
    if not url:
        raise RuntimeError("Define CPCMINI_DATABASE_URL (p. ej. sqlite:///data/cpcmini.db)")
    return str(url)


def run_migrations_offline() -> None:
    context.configure(
        url=_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
