"""
Ingredient availability domain model.

Table: ingredient_availability_history

One row per unavailability REPORT event (append-on-report, close-on-resolve).
Inherits from BaseModel — rows are mutated on resolution (resuelto_en, resuelto_por),
so AppendOnlyBaseModel is intentionally NOT used here (unlike HistorialEstadoPedido).

See design.md D6 for the full lifecycle and naming rationale.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models import BaseModel


class HistorialDisponibilidadIngrediente(BaseModel):
    """
    Audit/event log for ingredient kitchen-availability reports.

    Lifecycle:
    - Created (append) when a cook marks an ingredient unavailable.
    - Mutated (close) when an admin resolves the shortage:
        resuelto_en = now(), resuelto_por = admin_user_id.

    Derived state (no separate status column — D6):
    - pendiente: resuelto_en IS NULL
    - resuelto:  resuelto_en IS NOT NULL

    An ingredient can go unavailable→available many times; each cycle produces
    a new row. Resolved rows are KEPT for audit.
    """

    __tablename__ = "ingredient_availability_history"

    ingrediente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Cook who reported the shortage.
    reportado_por: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Order where the cook detected the shortage (traceability — not the source of activo).
    pedido_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # NULL = pending; set on resolution (admin action).
    resuelto_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    # Admin who resolved this report. NULL until resolved.
    resuelto_por: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Relationships (lazy by default — callers eager-load as needed)
    ingrediente: Mapped["features.catalog.models.Ingrediente"] = relationship(
        "Ingrediente",
        foreign_keys=[ingrediente_id],
        lazy="select",
    )
    cook: Mapped["features.users.models.Usuario"] = relationship(
        "Usuario",
        foreign_keys=[reportado_por],
        lazy="select",
    )
    pedido: Mapped["features.orders.models.Pedido"] = relationship(
        "Pedido",
        foreign_keys=[pedido_id],
        lazy="select",
    )
    resolver: Mapped[Optional["features.users.models.Usuario"]] = relationship(
        "Usuario",
        foreign_keys=[resuelto_por],
        lazy="select",
    )

    @property
    def es_pendiente(self) -> bool:
        """True when the shortage has not been resolved yet."""
        return self.resuelto_en is None

    def __repr__(self) -> str:
        estado = "pendiente" if self.es_pendiente else "resuelto"
        return (
            f"<HistorialDisponibilidadIngrediente("
            f"id={self.id}, ingrediente_id={self.ingrediente_id}, "
            f"pedido_id={self.pedido_id}, {estado})>"
        )
