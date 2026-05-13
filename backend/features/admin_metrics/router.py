"""
Admin metrics router.

All endpoints require ADMIN role.
Prefix (registered in main.py): /api/v1/admin/metricas

Routes:
  GET /resumen             — US-056 general summary (totals + ticket promedio)
  GET /ventas-por-periodo  — US-057 sales evolution by day/week/month
  GET /top-productos       — US-058 best-selling products ranking
  GET /pedidos-por-estado  — US-059 orders distribution by state
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from features.admin_metrics.schemas import (
    PedidosPorEstadoResponse,
    ResumenMetricas,
    TopProductosResponse,
    VentasPorPeriodoResponse,
)
from features.admin_metrics.service import Granularidad, MetricsService
from features.auth.dependencies import require_role

router = APIRouter()

_service = MetricsService()


@router.get(
    "/resumen",
    response_model=ResumenMetricas,
    summary="Resumen de métricas generales (Admin)",
    description=(
        "Devuelve totales de ventas, cantidad de pedidos, ticket promedio y "
        "total de usuarios para el periodo indicado. "
        "Si no se indica rango de fechas, abarca todo el histórico. "
        "Requiere rol ADMIN. (US-056)"
    ),
)
def get_resumen(
    desde: Optional[date] = Query(None, description="Inicio del periodo (inclusive)"),
    hasta: Optional[date] = Query(None, description="Fin del periodo (inclusive)"),
    _current_user=Depends(require_role("ADMIN")),
) -> ResumenMetricas:
    """GET /admin/metricas/resumen — general summary."""
    return _service.get_resumen(desde=desde, hasta=hasta)


@router.get(
    "/ventas-por-periodo",
    response_model=VentasPorPeriodoResponse,
    summary="Evolución de ventas por periodo (Admin)",
    description=(
        "Devuelve la evolución de ventas agrupada por día, semana o mes. "
        "Cada punto incluye monto total y cantidad de pedidos. "
        "Requiere rol ADMIN. (US-057)"
    ),
)
def get_ventas_por_periodo(
    desde: Optional[date] = Query(None, description="Inicio del periodo (inclusive)"),
    hasta: Optional[date] = Query(None, description="Fin del periodo (inclusive)"),
    granularidad: Granularidad = Query(
        Granularidad.dia,
        description="Granularidad de agrupación: dia | semana | mes",
    ),
    _current_user=Depends(require_role("ADMIN")),
) -> VentasPorPeriodoResponse:
    """GET /admin/metricas/ventas-por-periodo — sales timeline."""
    return _service.get_ventas_por_periodo(
        desde=desde, hasta=hasta, granularidad=granularidad
    )


@router.get(
    "/top-productos",
    response_model=TopProductosResponse,
    summary="Top productos más vendidos (Admin)",
    description=(
        "Devuelve el ranking de los N productos más vendidos, ordenados por "
        "cantidad total vendida (descendente). Incluye ingresos generados. "
        "top mínimo 1, máximo 50, default 10. "
        "Requiere rol ADMIN. (US-058)"
    ),
)
def get_top_productos(
    desde: Optional[date] = Query(None, description="Inicio del periodo (inclusive)"),
    hasta: Optional[date] = Query(None, description="Fin del periodo (inclusive)"),
    top: int = Query(10, ge=1, le=50, description="Cantidad de productos a retornar"),
    _current_user=Depends(require_role("ADMIN")),
) -> TopProductosResponse:
    """GET /admin/metricas/top-productos — best-sellers ranking."""
    return _service.get_top_productos(desde=desde, hasta=hasta, top=top)


@router.get(
    "/pedidos-por-estado",
    response_model=PedidosPorEstadoResponse,
    summary="Distribución de pedidos por estado (Admin)",
    description=(
        "Devuelve la cantidad de pedidos agrupados por estado para el periodo indicado. "
        "Útil para identificar cuellos de botella en el proceso. "
        "Requiere rol ADMIN. (US-059)"
    ),
)
def get_pedidos_por_estado(
    desde: Optional[date] = Query(None, description="Inicio del periodo (inclusive)"),
    hasta: Optional[date] = Query(None, description="Fin del periodo (inclusive)"),
    _current_user=Depends(require_role("ADMIN")),
) -> PedidosPorEstadoResponse:
    """GET /admin/metricas/pedidos-por-estado — order state distribution."""
    return _service.get_pedidos_por_estado(desde=desde, hasta=hasta)
