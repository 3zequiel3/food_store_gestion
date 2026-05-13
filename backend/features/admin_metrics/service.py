"""
Admin metrics service — orchestrates repository calls and Python-level aggregations.

D1: READ-ONLY. Uses UnitOfWork to obtain a session so that the test conftest
    monkeypatch on get_session_factory propagates correctly. No commit is issued
    (context manager still calls commit on clean exit, which is a no-op for
    SELECT-only transactions).
D2: Period grouping (day/week/month) done in Python after raw row fetch —
    avoids PostgreSQL-specific DATE_TRUNC that is unavailable in SQLite tests.
D3: All Decimal values converted to str before being placed in response schemas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from features.admin_metrics.repository import MetricsRepository
from features.admin_metrics.schemas import (
    DistribucionEstado,
    PedidosPorEstadoResponse,
    ProductoTop,
    PuntoPeriodo,
    ResumenMetricas,
    TopProductosResponse,
    VentasPorPeriodoResponse,
)
from shared.unit_of_work import UnitOfWork


class Granularidad(str, Enum):
    """Temporal grouping granularity for the sales-over-time chart (US-057)."""

    dia = "dia"
    semana = "semana"
    mes = "mes"


def _periodo_key(dt, granularidad: Granularidad) -> str:
    """
    Map a datetime to a period label string.

    - dia   → "YYYY-MM-DD"
    - semana → "YYYY-WNN"  (ISO week number, zero-padded)
    - mes   → "YYYY-MM"
    """
    if granularidad == Granularidad.dia:
        return dt.strftime("%Y-%m-%d")
    if granularidad == Granularidad.semana:
        return dt.strftime("%Y-W%W")
    # mes
    return dt.strftime("%Y-%m")


class MetricsService:
    """
    Metrics service — builds response schemas from repository data.

    Instantiated once at module level (like other feature services),
    session is created per call to avoid connection leaks.
    """

    def get_resumen(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> ResumenMetricas:
        """US-056 — General metrics summary."""
        with UnitOfWork() as uow:
            repo = MetricsRepository(uow.session)
            total_ventas, total_pedidos = repo.get_resumen_pedidos(desde, hasta)
            total_usuarios = repo.get_total_usuarios()

        if total_pedidos > 0:
            ticket_promedio = total_ventas / total_pedidos
        else:
            ticket_promedio = Decimal("0")

        return ResumenMetricas(
            total_ventas=str(total_ventas),
            total_pedidos=total_pedidos,
            ticket_promedio=str(ticket_promedio.quantize(Decimal("0.01"))),
            total_usuarios=total_usuarios,
            periodo_desde=desde,
            periodo_hasta=hasta,
        )

    def get_ventas_por_periodo(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        granularidad: Granularidad = Granularidad.dia,
    ) -> VentasPorPeriodoResponse:
        """US-057 — Sales evolution grouped by day/week/month."""
        with UnitOfWork() as uow:
            repo = MetricsRepository(uow.session)
            raw_rows = repo.get_ventas_raw(desde, hasta)

        # Group in Python (D2 — DB-agnostic)
        grouped: dict[str, dict] = defaultdict(lambda: {"total": Decimal("0"), "count": 0})
        for creado_en, total in raw_rows:
            key = _periodo_key(creado_en, granularidad)
            grouped[key]["total"] += total
            grouped[key]["count"] += 1

        puntos = [
            PuntoPeriodo(
                periodo=periodo,
                total_ventas=str(data["total"]),
                cantidad_pedidos=data["count"],
            )
            for periodo, data in sorted(grouped.items())
        ]

        return VentasPorPeriodoResponse(
            granularidad=granularidad.value,
            puntos=puntos,
        )

    def get_top_productos(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        top: int = 10,
    ) -> TopProductosResponse:
        """US-058 — Top N best-selling products."""
        # Clamp top to reasonable bounds
        top = max(1, min(top, 50))

        with UnitOfWork() as uow:
            repo = MetricsRepository(uow.session)
            rows = repo.get_top_productos(desde, hasta, top)

        productos = [
            ProductoTop(
                producto_id=producto_id,
                nombre=nombre,
                cantidad_total=cantidad,
                ingreso_total=str(ingreso),
            )
            for producto_id, nombre, cantidad, ingreso in rows
        ]

        return TopProductosResponse(top=top, productos=productos)

    def get_pedidos_por_estado(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> PedidosPorEstadoResponse:
        """US-059 — Orders distribution across states."""
        with UnitOfWork() as uow:
            repo = MetricsRepository(uow.session)
            rows = repo.get_pedidos_por_estado(desde, hasta)

        distribucion = [
            DistribucionEstado(estado_codigo=estado, cantidad=cantidad)
            for estado, cantidad in rows
        ]

        return PedidosPorEstadoResponse(distribucion=distribucion)
