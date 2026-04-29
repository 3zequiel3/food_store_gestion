"""
Base ORM model classes shared by all domain entities.

Two base classes are provided:
- BaseModel: for all regular entities (id + creado_en + actualizado_en + eliminado_en).
- AppendOnlyBaseModel: for log/history entities that must never be updated
  (id + creado_en only — no actualizado_en, no eliminado_en).

Both use PK BIGSERIAL (Integer autoincrement) and TIMESTAMPTZ columns, per ERD v5.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class BaseModel(Base):
    """
    Abstract base model for all domain entities.

    Provides:
    - id: BIGSERIAL primary key (Integer autoincrement).
    - creado_en: creation timestamp with timezone (server default: now()).
    - actualizado_en: last-update timestamp with timezone (server default + onupdate: now()).
    - eliminado_en: soft-delete timestamp with timezone (nullable, default None).

    Repositories MUST filter WHERE eliminado_en IS NULL by default.
    Use query_with_deleted() for admin/audit queries that need deleted records.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    eliminado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class AppendOnlyBaseModel(Base):
    """
    Abstract base model for append-only / log-style entities.

    Provides:
    - id: BIGSERIAL primary key.
    - creado_en: creation timestamp with timezone (server default: now()).

    Intentionally EXCLUDES actualizado_en and eliminado_en to make it
    physically impossible to accidentally update or soft-delete history rows.
    Used by: HistorialEstadoPedido (RN-PA02 trazabilidad de transiciones).
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
