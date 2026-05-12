"""
Orders schemas — Pydantic v2 models for the order creation endpoint.

Design decisions:
- D10: extra="forbid" in CrearPedidoRequest and ItemPedidoRequest prevents
  anti-smuggling (client cannot inject total, estado_codigo, usuario_id, etc.)
- D11: Decimal end-to-end, never float.
- D9: Naming in castellano (domain language of the project).

Out of scope (belong to order-visualization-backend #17):
- DetallePedidoRead
- HistorialEstadoRead
- PedidoDetail
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemPedidoRequest(BaseModel):
    """
    A single line item in a new order request.

    D10 — extra="forbid": rejects any field not declared here.
    This prevents clients from injecting precio_snapshot, nombre_snapshot, etc.
    """

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., ge=1, description="ID del producto (>= 1)")
    cantidad: int = Field(..., ge=1, le=999, description="Cantidad (1-999)")
    personalizacion: Optional[list[int]] = Field(
        default=None,
        max_length=20,
        description="IDs de ingredientes personalizados (máx. 20). PG ARRAY(Integer) — D2.",
    )

    @field_validator("personalizacion")
    @classmethod
    def _ids_positivos(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Reject personalizacion lists containing IDs <= 0."""
        if v is None:
            return v
        if any(i <= 0 for i in v):
            raise ValueError("Cada ingredient_id en personalizacion debe ser >= 1")
        return v


class CrearPedidoRequest(BaseModel):
    """
    Request body for POST /api/v1/pedidos.

    D10 — extra="forbid": rejects total, estado_codigo, usuario_id, etc.
    D10 — str_strip_whitespace: avoids padding in forma_pago_codigo and notas.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    items: list[ItemPedidoRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Líneas del pedido (1-50 items).",
    )
    forma_pago_codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código semántico de la forma de pago (ej. MERCADOPAGO).",
    )
    direccion_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="ID de la dirección de entrega. None = retiro en local (D1, D5).",
    )
    notas: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Notas opcionales para el repartidor o el local.",
    )


class AvanzarEstadoRequest(BaseModel):
    """
    Request body for PATCH /api/v1/pedidos/{pedido_id}/estado.

    D5 — doble defensa: CONFIRMADO is excluded from Literal so FastAPI returns
    422 before the service is even called. The service also rejects it as a
    second defense.
    D7 — motivo is optional here; the service enforces it conditionally for
    cancellations from CONFIRMADO or EN_PREPARACION.
    """

    nuevo_estado: Literal["CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"]
    motivo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Motivo del cambio de estado (obligatorio para cancelaciones desde CONFIRMADO o EN_PREPARACION).",
    )


class PedidoRead(BaseModel):
    """
    Compact read schema for the order creation response (201) and state transitions.

    Returns only what the client needs: id, estado_codigo, total, creado_en.

    Full detail (items, historial) belongs to order-visualization-backend #17.

    D11 — Decimal end-to-end: Pydantic v2 serializes Decimal as string
    (no precision loss, safe for monetary values).

    Note: field names match the ORM model (Spanish naming convention — D9).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_codigo: str
    total: Decimal
    creado_en: datetime
