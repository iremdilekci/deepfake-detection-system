"""
Alembic migration ortam yapılandırması.
config.py'deki bağlantı bilgilerini kullanır.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from config import settings
from database import Base

# Modelleri yükle — metadata eksiksiz olsun
import models  # noqa: F401

# Alembic Config nesnesi (.ini dosyasındaki değerler)
config = context.config

# Logging ayarları
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# .env'den gelen sync URL'i kullan
config.set_main_option("sqlalchemy.url", settings.db_url_sync)

# Autogenerate için target metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline modda migration çalıştır (SQL dosyası üretir)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online modda migration çalıştır (doğrudan DB'ye uygular)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
