"""
Address domain model: DireccionEntrega (delivery_addresses).

Users can have multiple delivery addresses; one can be marked as principal.
When a Pedido is placed, the selected address is denormalized into
Pedido.direccion_snapshot (text) so address changes don't affect past orders.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel


class DireccionEntrega(BaseModel):
    """
    Delivery address associated with a user.

    - ``es_principal``: user's default address for new orders (True/False).
    - ``referencia``: optional free-text landmark / delivery instructions.
    """

    __tablename__ = "delivery_addresses"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calle: Mapped[str] = mapped_column(String(255), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_postal: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship back to user
    usuario: Mapped["backend.features.users.models.Usuario"] = relationship(
        "Usuario",
        back_populates="direcciones",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<DireccionEntrega(id={self.id}, user_id={self.user_id}, calle={self.calle!r})>"
