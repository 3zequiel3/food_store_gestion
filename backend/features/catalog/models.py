"""
Catalog ORM models: reference tables that drive FK lookups.

Tables defined here:
- roles           (PK Integer, IDs stable 1..5)
- payment_methods (PK VARCHAR semántica)
- order_states    (PK VARCHAR semántica, con orden y es_terminal)
- categories      (árbol autoreferencial)
- ingredients     (con flag es_alergeno)
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models import BaseModel


# ---------------------------------------------------------------------------
# Rol — tabla catálogo con IDs estables (1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT, 5=COCINA)
# ---------------------------------------------------------------------------


class Rol(BaseModel):
    """
    User role catalog.

    IDs are stable (hardcoded in seed) so application code can reference
    them by integer constant without joins. The string `codigo` is the
    human-readable identifier used in logs and API responses.
    """

    __tablename__ = "roles"

    # PK is an Integer (not autoincrement — seed inserts IDs 1..5 explicitly)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Rol(id={self.id}, codigo={self.codigo!r})>"


# ---------------------------------------------------------------------------
# FormaPago — PK semántica VARCHAR (MERCADOPAGO / EFECTIVO / TRANSFERENCIA)
# ---------------------------------------------------------------------------


class FormaPago(BaseModel):
    """
    Payment method catalog.

    Uses a semantic VARCHAR primary key so query filters are self-documenting:
    ``WHERE forma_pago_codigo = 'MERCADOPAGO'``
    """

    __tablename__ = "payment_methods"

    # Override the BIGSERIAL id from BaseModel with a VARCHAR PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(
        String(50), primary_key=False, unique=True, nullable=False
    )
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    habilitada: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<FormaPago(codigo={self.codigo!r}, habilitada={self.habilitada})>"


# ---------------------------------------------------------------------------
# EstadoPedido — PK semántica VARCHAR con orden y flag terminal
# ---------------------------------------------------------------------------


class EstadoPedido(BaseModel):
    """
    Order state catalog.

    - ``orden``: integer for UI ordering of the workflow steps.
    - ``es_terminal``: True for ENTREGADO and CANCELADO (no further transitions allowed).
    """

    __tablename__ = "order_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    es_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<EstadoPedido(codigo={self.codigo!r}, orden={self.orden})>"


# ---------------------------------------------------------------------------
# Categoria — árbol autoreferencial (padre_id nullable)
# ---------------------------------------------------------------------------


class Categoria(BaseModel):
    """
    Product category with optional parent for tree structure.

    Self-referential FK on padre_id enables multi-level category trees.
    ``remote_side=[id]`` is required by SQLAlchemy to resolve the direction
    of the relationship.
    """

    __tablename__ = "categories"

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    padre_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Self-referential relationships
    padre: Mapped[Optional["Categoria"]] = relationship(
        "Categoria",
        back_populates="hijos",
        remote_side="Categoria.id",
        foreign_keys=[padre_id],
    )
    hijos: Mapped[List["Categoria"]] = relationship(
        "Categoria",
        back_populates="padre",
        foreign_keys=[padre_id],
    )

    def __repr__(self) -> str:
        return f"<Categoria(id={self.id}, nombre={self.nombre!r})>"


# ---------------------------------------------------------------------------
# Ingrediente — con flag de alérgeno
# ---------------------------------------------------------------------------


class Ingrediente(BaseModel):
    """
    Ingredient entity.

    ``es_alergeno`` drives the allergen-warning UI per spec.
    ``es_removible`` controls whether the ingredient can be removed by the
    client when ordering (global property, not per-product).
    ``nombre`` is UNIQUE because ingredients are reused across products.
    """

    __tablename__ = "ingredients"

    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    es_alergeno: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_removible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Ingrediente(id={self.id}, nombre={self.nombre!r})>"
