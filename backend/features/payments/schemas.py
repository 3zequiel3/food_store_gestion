"""
Payment schemas (Pydantic v2).

PagoCreate — request body for POST /api/v1/pagos
PagoRead   — response for payment endpoints (includes optional init_point)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PagoCreate(BaseModel):
    pedido_id: int

    model_config = ConfigDict(extra="forbid")


class PagoRead(BaseModel):
    id: int
    pedido_id: int
    monto: Decimal
    forma_pago_codigo: str
    mp_payment_id: Optional[str] = None
    mp_status: Optional[str] = None
    idempotency_key: str
    creado_en: datetime
    actualizado_en: datetime
    init_point: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
