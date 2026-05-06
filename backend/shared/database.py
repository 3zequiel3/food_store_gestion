"""
Database engine, session factory, and SQLAlchemy declarative Base.

This module is the single source of truth for:
- MetaData (with deterministic naming conventions for Alembic autogenerate)
- Base (DeclarativeBase used by all ORM models)
- engine / SessionLocal (used by dependencies.py and the seed script)
"""

import os
from typing import Generator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Deterministic naming convention so Alembic generates stable constraint names
# across runs and across databases. Format:
#   ix_<table>_<column>
#   uq_<table>_<column>
#   ck_<table>_<constraint_name>
#   fk_<table>_<column>_<referred_table>
#   pk_<table>
NAMING_CONVENTION: dict = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base with deterministic naming conventions.

    All ORM models in the project MUST inherit from this class so that
    Alembic autogenerate picks them up and constraint names remain stable.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _get_database_url() -> str:
    """Read DATABASE_URL from environment. Raises if not set."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Fallback to config for backward compatibility when running the app
        try:
            from backend.config import settings  # noqa: PLC0415
            return settings.DATABASE_URL
        except Exception:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Export it before running migrations or the seed script."
            )
    return url


# Lazy engine: built once on first import.
# Separate from the app engine in dependencies.py so the seed script
# and Alembic env.py can import this module standalone.
_engine = None
_SessionLocal = None


def get_engine():
    """Return (or lazily create) the SQLAlchemy engine."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = create_engine(
            _get_database_url(),
            echo=os.environ.get("LOG_LEVEL", "").upper() == "DEBUG",
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    """Return (or lazily create) the session factory."""
    global _SessionLocal  # noqa: PLW0603
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yield a SQLAlchemy session, commit on success,
    rollback on exception, always close.

    Usage:
        @router.get("/")
        def my_endpoint(db: Session = Depends(get_db)):
            ...

    Auto-commit semantics: a request that returns successfully (no
    exception bubbled up to the dependency) will commit any pending work.
    Services use ``session.flush()`` to obtain IDs and intermediate state,
    but the final persistence happens here. If the endpoint raises, the
    session is rolled back.

    For multi-step business operations that need explicit transactional
    control across multiple repositories, use ``get_uow`` from
    ``backend/dependencies.py`` instead.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
