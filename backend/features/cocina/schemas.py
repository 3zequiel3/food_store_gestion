"""
Pydantic schemas for the Kitchen Display System (KDS).

D6: REST endpoint returns minimal order snapshots for the KDS.
D5: WebSocket events carry the same minimal payload.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class CocinaPedidoItem(BaseModel):
    """Minimal item info for a kitchen order card."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    nombre_snapshot: str
    cantidad: int
    personalizacion: Optional[list[int]] = None
    notas: Optional[str] = None


class CocinaPedidoResponse(BaseModel):
    """
    Order snapshot for the KDS.

    - estado: current state code (CONFIRMADO or EN_PREPARACION).
    - cocina_entry_at: timestamp of the transition to CONFIRMADO (kitchen entry time, RN-CO02).
    """

    id: int
    estado: str
    items: list[CocinaPedidoItem]
    notas: Optional[str] = None
    cocina_entry_at: datetime


# ---------------------------------------------------------------------------
# WebSocket event types
# ---------------------------------------------------------------------------

CocinaEventType = Literal[
    "pedido_confirmado",
    "pedido_en_preparacion",
    "pedido_terminado",
    "pedido_cancelado",
]


class CocinaEvent(BaseModel):
    """
    WebSocket event pushed to KDS screens.

    - type: event identifier (snake_case).
    - payload: minimal order snapshot (same shape as CocinaPedidoResponse).
    """

    type: CocinaEventType
    payload: CocinaPedidoResponse
