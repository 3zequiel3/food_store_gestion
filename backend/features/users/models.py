"""
User domain models: Usuario (users) and UsuarioRol pivot (user_roles).
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel, PivotBaseModel
from backend.features.catalog.models import Rol


class UsuarioRol(PivotBaseModel):
    """
    Many-to-many pivot between users and roles.

    Composite PK (user_id, role_id) — no surrogate id (ERD v5 §3.1, migration 20260428_0001).
    Inherits from PivotBaseModel (not BaseModel) to avoid the autoincrement `id` column
    that SQLite cannot combine with a composite primary key.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UsuarioRol(user_id={self.user_id}, role_id={self.role_id})>"


class Usuario(BaseModel):
    """
    User entity aligned with ERD v5.

    Key design decisions:
    - No `username` column: login is by email per RN-DA08.
    - No `role` direct FK: roles via M:N pivot `user_roles` (RN-DA01).
    - `password_hash`: bcrypt hash stored as opaque string.
    - `is_active`: quick flag to disable an account without soft-deleting it.
    - `eliminado_en` (from BaseModel): soft delete for account removal.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # M:N relationship to Rol via user_roles pivot
    roles: Mapped[List[Rol]] = relationship(
        "Rol",
        secondary="user_roles",
        viewonly=False,
        lazy="select",
    )

    # Back-references (defined in other modules — use string refs to avoid circular imports)
    pedidos: Mapped[List] = relationship(
        "Pedido",
        back_populates="usuario",
        cascade="all, delete-orphan",
        lazy="select",
    )
    refresh_tokens: Mapped[List] = relationship(
        "RefreshToken",
        back_populates="usuario",
        cascade="all, delete-orphan",
        lazy="select",
    )
    direcciones: Mapped[List] = relationship(
        "DireccionEntrega",
        back_populates="usuario",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Usuario(id={self.id}, email={self.email!r})>"
