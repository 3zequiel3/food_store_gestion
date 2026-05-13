"""
Catalog schemas — Pydantic v2 models for catalog reference endpoints.

These schemas expose reference data (payment methods, order states, roles)
for client-side selectors and dropdowns.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FormaPagoRead(BaseModel):
    """
    Payment method read schema for GET /api/v1/formas-pago.

    Only habilitada=True records are returned.
    """

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    habilitada: bool
