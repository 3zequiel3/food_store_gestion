"""
Pydantic schemas for the Kitchen Display System (KDS).

D6: REST endpoint returns minimal order snapshots for the KDS.
D5: WebSocket events carry the same minimal payload.
D10: Kitchen payload includes full ingredient list and resolved exclusion names
     so the cook sees ingredient names, not raw IDs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class IngredienteInfo(BaseModel):
    """
    Minimal ingredient info included in the kitchen order item payload.

    Design D10: surfaces id, nombre, and es_removible so the cook can
    see the full recipe and which ingredients are removable.

    `activo` reflects the kitchen-availability flag (D6 — Phase 6). When
    false, the FSM guard `_check_ingredient_availability_guard` blocks the
    pedido from advancing; the frontend uses this to render the card as
    "blocked by faltante" and disable the advance button.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    es_removible: bool
    activo: bool


class CocinaPedidoItem(BaseModel):
    """Minimal item info for a kitchen order card.

    Design D10 (P1.4 backend): includes the product's full ingredient list
    with names and resolves personalizacion exclusion IDs to names.
    """

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    nombre_snapshot: str
    cantidad: int
    personalizacion: Optional[list[int]] = None
    notas: Optional[str] = None
    # D10: full ingredient list with names (avoids "Ingrediente #N" in the KDS)
    ingredientes: list[IngredienteInfo] = []
    # D10: exclusion IDs resolved to ingredient names for the cook
    exclusiones_nombres: list[str] = []


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
