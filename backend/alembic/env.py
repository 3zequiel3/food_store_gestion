"""
Alembic environment configuration.

- DATABASE_URL is read from the environment variable DATABASE_URL.
- Base.metadata from backend.shared.database is used as target_metadata so
  that autogenerate compares the current ORM models against the live schema.
- All feature model modules are imported here so SQLAlchemy registers every
  table in Base.metadata before autogenerate runs.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy import engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Make "backend" package importable when running from the backend/ directory.
# The alembic.ini sets prepend_sys_path = .. so the project root is on sys.path,
# but we also add the backend parent explicitly just in case.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent  # backend/alembic/
_BACKEND_PARENT = _HERE.parent.parent    # project root (contains backend/)
if str(_BACKEND_PARENT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PARENT))

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Inject DATABASE_URL from environment into Alembic config.
# The sqlalchemy.url key in alembic.ini is intentionally left blank.
# ---------------------------------------------------------------------------
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    config.set_main_option("sqlalchemy.url", _database_url)
else:
    # Fallback: try to read from backend.config (app running with .env)
    try:
        from backend.config import settings  # noqa: PLC0415
        config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    except Exception:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Export it before running Alembic commands.\n"
            "  export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/foodstore_dev"
        )

# ---------------------------------------------------------------------------
# Import Base and all model modules so SQLAlchemy populates metadata.
# ADD new model modules here as new features are created.
# ---------------------------------------------------------------------------
from backend.shared.database import Base  # noqa: E402, F401

# Catalog models (roles, payment_methods, order_states, categories, ingredients)
import backend.features.catalog.models  # noqa: F401, E402

# User identity models (users, user_roles)
import backend.features.users.models  # noqa: F401, E402

# Auth models (refresh_tokens)
import backend.features.auth.models  # noqa: F401, E402

# Address models (delivery_addresses)
import backend.features.addresses.models  # noqa: F401, E402

# Product models (products, product_categories, product_ingredients)
import backend.features.products.models  # noqa: F401, E402

# Order models (orders, order_items, order_state_history)
import backend.features.orders.models  # noqa: F401, E402

# Payment models (payments)
import backend.features.payments.models  # noqa: F401, E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
