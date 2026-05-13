"""
Order domain models: Pedido, DetallePedido, HistorialEstadoPedido.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import AppendOnlyBaseModel, BaseModel


# ---------------------------------------------------------------------------
# Pedido
# ---------------------------------------------------------------------------

class Pedido(BaseModel):
    """
    Order entity aligned with ERD v5 (§3.3).

    Key fields:
    - direccion_entrega_id: FK to the delivery address at order time. NULLABLE —
      NULL means "retiro en local" (in-store pickup). ON DELETE SET NULL preserves
      the snapshot even if the user later deletes the address (RN-DA06, D1).
    - direccion_snapshot: denormalized text snapshot of the address so that
      subsequent address changes do not affect this order. NULL for in-store pickup.
    - forma_pago_codigo: FK to payment_methods.codigo (VARCHAR semántica).
    - estado_codigo: FK to order_states.codigo (VARCHAR semántica), default PENDIENTE.
    - costo_envio: shipping cost. Decimal("50.00") with address, Decimal("0.00")
      for in-store pickup (D5, v1 fixed rate).
    """

    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    direccion_entrega_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("delivery_addresses.id", ondelete="SET NULL"),
        nullable=True,
    )
    direccion_snapshot: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    costo_envio: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    forma_pago_codigo: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("payment_methods.codigo", ondelete="RESTRICT"),
        nullable=False,
    )
    estado_codigo: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("order_states.codigo", ondelete="RESTRICT"),
        nullable=False,
        default="PENDIENTE",
        index=True,
    )
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    usuario: Mapped["backend.features.users.models.Usuario"] = relationship(
        "Usuario",
        back_populates="pedidos",
        lazy="select",
    )
    items: Mapped[List["DetallePedido"]] = relationship(
        "DetallePedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="select",
    )
    pagos: Mapped[List["backend.features.payments.models.Pago"]] = relationship(
        "Pago",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="select",
    )
    historial: Mapped[List["HistorialEstadoPedido"]] = relationship(
        "HistorialEstadoPedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Pedido(id={self.id}, user_id={self.user_id}, total={self.total}, estado={self.estado_codigo!r})>"


# ---------------------------------------------------------------------------
# DetallePedido
# ---------------------------------------------------------------------------

class DetallePedido(BaseModel):
    """
    Order line item with snapshots of product name and price at order time.

    - nombre_snapshot / precio_snapshot: denormalized so product edits
      don't retroactively change historical orders.
    - personalizacion: optional array of ingredient IDs that were removed or
      added. PG ARRAY(Integer). FK integrity at application level only
      (PG doesn't support FK on arrays).
    """

    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_order_items_cantidad_positiva"),
    )

    pedido_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    precio_snapshot: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    personalizacion: Mapped[Optional[list]] = mapped_column(
        ARRAY(Integer), nullable=True
    )

    # Relationship back to order
    pedido: Mapped["Pedido"] = relationship(
        "Pedido",
        back_populates="items",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<DetallePedido(id={self.id}, pedido_id={self.pedido_id}, "
            f"nombre_snapshot={self.nombre_snapshot!r}, cantidad={self.cantidad})>"
        )


# ---------------------------------------------------------------------------
# HistorialEstadoPedido (append-only)
# ---------------------------------------------------------------------------

class HistorialEstadoPedido(AppendOnlyBaseModel):
    """
    Append-only log of order state transitions (RN-PA02 trazabilidad).

    Inherits from AppendOnlyBaseModel — no actualizado_en, no eliminado_en.
    This makes accidental UPDATEs physically impossible at the ORM layer.

    - estado_anterior_codigo: nullable for the first transition (no prior state).
    - cambiado_por_id: nullable for system-triggered transitions.
    """

    __tablename__ = "order_state_history"

    pedido_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado_anterior_codigo: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("order_states.codigo", ondelete="RESTRICT"),
        nullable=True,
    )
    estado_nuevo_codigo: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("order_states.codigo", ondelete="RESTRICT"),
        nullable=False,
    )
    cambiado_por_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    motivo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationship back to order
    pedido: Mapped["Pedido"] = relationship(
        "Pedido",
        back_populates="historial",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<HistorialEstadoPedido(id={self.id}, pedido_id={self.pedido_id}, "
            f"{self.estado_anterior_codigo!r} -> {self.estado_nuevo_codigo!r})>"
        )
