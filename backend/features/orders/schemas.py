"""
Orders schemas — Pydantic v2 models for order endpoints.

Design decisions:
- D10: extra="forbid" in CrearPedidoRequest and ItemPedidoRequest prevents
  anti-smuggling (client cannot inject total, estado_codigo, usuario_id, etc.)
- D11: Decimal end-to-end, never float.
- D9: Naming in castellano (domain language of the project).
- D4: list schemas (PedidoListItem) do NOT include relations; only PedidoDetalle
  eager-loads items/historial/pagos.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    nuevo_estado: Literal["CANCELADO", "EN_PREPARACION", "TERMINADO", "ENTREGADO"]
    motivo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Motivo del cambio de estado (obligatorio para cancelaciones desde CONFIRMADO o EN_PREPARACION).",
    )


class TransicionarRequest(BaseModel):
    """
    Request body for POST /api/v1/pedidos/{pedido_id}/transicionar.

    Generic state transition — any target state allowed by the FSM.
    motivo is required for CANCELADO_ADMIN transitions.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    estado_codigo_destino: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código del estado destino (ej. CANCELADO_ADMIN).",
    )
    motivo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Motivo de la transición (obligatorio para CANCELADO_ADMIN).",
    )


class TransicionarResponse(BaseModel):
    """Response for POST /api/v1/pedidos/{pedido_id}/transicionar."""

    pedido_id: int
    estado_anterior: str
    estado_nuevo: str
    historial: list[HistorialItem]


class PedidoRead(BaseModel):
    """
    Compact read schema for the order creation response (201) and state transitions.

    Returns only what the client needs: id, estado_codigo, total, creado_en.

    D11 — Decimal end-to-end: Pydantic v2 serializes Decimal as string
    (no precision loss, safe for monetary values).

    Note: field names match the ORM model (Spanish naming convention — D9).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_codigo: str
    total: Decimal
    creado_en: datetime


# ---------------------------------------------------------------------------
# Visualization schemas (order-visualization-backend #17)
# ---------------------------------------------------------------------------


class PedidoListItem(BaseModel):
    """Compact schema for order list items — no relations, no N+1."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_codigo: str
    total: Decimal
    costo_envio: Decimal
    forma_pago_codigo: str
    creado_en: datetime
    items_count: int


class PaginatedPedidos(BaseModel):
    """Paginated order list — shape matches productos/categorias convention (D6)."""

    items: list[PedidoListItem]
    total: int
    page: int
    limit: int


class ItemDetalle(BaseModel):
    """Order line item with immutable snapshots."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    cantidad: int
    personalizacion: Optional[list[int]] = None


class HistorialItem(BaseModel):
    """Single entry in the order state transition log."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_anterior_codigo: Optional[str] = None
    estado_nuevo_codigo: str
    cambiado_por_id: Optional[int] = None
    motivo: Optional[str] = None
    creado_en: datetime


class PagoSummary(BaseModel):
    """Payment summary for order detail — maps mp_status to status."""

    id: int
    status: str
    monto: Decimal
    fecha: datetime


class PedidoDetalle(BaseModel):
    """Full order detail with eager-loaded items, historial, and pagos."""

    id: int
    user_id: int
    estado_codigo: str
    total: Decimal
    costo_envio: Decimal
    forma_pago_codigo: str
    direccion_snapshot: Optional[str] = None
    notas: Optional[str] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None
    items: list[ItemDetalle]
    historial: list[HistorialItem]
    pagos: list[PagoSummary]


_ESTADOS_PEDIDO = Literal[
    "PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "TERMINADO", "ENTREGADO", "CANCELADO"
]


class PedidoListFilters(BaseModel):
    """
    Query params for GET /api/v1/pedidos.

    Internal model — not exposed as response schema. FastAPI reads each field
    from the query string via Annotated[PedidoListFilters, Query()].
    """

    estado: Optional[_ESTADOS_PEDIDO] = None
    desde: Optional[date] = None
    hasta: Optional[date] = None
    q: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _validate_rango_fechas(self) -> "PedidoListFilters":
        if (
            self.desde is not None
            and self.hasta is not None
            and self.desde > self.hasta
        ):
            raise ValueError("desde no puede ser posterior a hasta")
        return self
