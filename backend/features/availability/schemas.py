"""
Pydantic schemas for the ingredient availability API endpoints.

D6 / Phase 6 — admin Faltantes view (open shortages + resolve action).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ShortageReportItem(BaseModel):
    """
    Serialized view of one HistorialDisponibilidadIngrediente row.
    Returned by GET /api/v1/availability/faltantes.
    """

    id: int
    ingrediente_id: int
    ingrediente_nombre: Optional[str] = None  # populated if joined
    reportado_por: int
    pedido_id: int
    creado_en: datetime
    resuelto_en: Optional[datetime] = None
    resuelto_por: Optional[int] = None

    class Config:
        from_attributes = True


class ResolveRequest(BaseModel):
    """
    Optional request body for the resolve endpoint.
    The action label is informational; no label → defaults to "solucionado".
    """

    accion: str = "solucionado"  # "ingrediente comprado" | "solucionado"


class ResolveResponse(BaseModel):
    """Response from POST /api/v1/availability/faltantes/{ingrediente_id}/resolver."""

    ok: bool
    ingrediente_id: int
    rows_closed: int
