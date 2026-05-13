"""
Admin metrics response schemas.

D3: All monetary values (Decimal) are serialized as strings to avoid
JSON precision loss. Use `str(decimal_value)` before returning.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ResumenMetricas(BaseModel):
    """
    General metrics summary (US-056).

    Fields:
    - total_ventas: sum of Pedido.total for the period (as string).
    - total_pedidos: count of orders in the period.
    - ticket_promedio: total_ventas / total_pedidos (as string), "0" when no orders.
    - total_usuarios: count of active (non-soft-deleted) users.
    - periodo_desde / periodo_hasta: echoed back from query params.
    """

    model_config = ConfigDict(from_attributes=True)

    total_ventas: str
    total_pedidos: int
    ticket_promedio: str
    total_usuarios: int
    periodo_desde: Optional[date] = None
    periodo_hasta: Optional[date] = None


class PuntoPeriodo(BaseModel):
    """Single data point for the sales-over-time chart (US-057)."""

    model_config = ConfigDict(from_attributes=True)

    periodo: str          # "2026-05-01" (dia) | "2026-W18" (semana) | "2026-05" (mes)
    total_ventas: str     # Decimal as string
    cantidad_pedidos: int


class VentasPorPeriodoResponse(BaseModel):
    """Sales evolution grouped by granularity (US-057)."""

    model_config = ConfigDict(from_attributes=True)

    granularidad: str
    puntos: List[PuntoPeriodo]


class ProductoTop(BaseModel):
    """Single entry in the top-products ranking (US-058)."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    nombre: str
    cantidad_total: int
    ingreso_total: str    # Decimal as string


class TopProductosResponse(BaseModel):
    """Ranked list of best-selling products (US-058)."""

    model_config = ConfigDict(from_attributes=True)

    top: int
    productos: List[ProductoTop]


class DistribucionEstado(BaseModel):
    """Count of orders in a single state (US-059)."""

    model_config = ConfigDict(from_attributes=True)

    estado_codigo: str
    cantidad: int


class PedidosPorEstadoResponse(BaseModel):
    """Distribution of orders across all states (US-059)."""

    model_config = ConfigDict(from_attributes=True)

    distribucion: List[DistribucionEstado]
