"""
Admin metrics repository — read-only aggregation queries.

D2: Date-grouping is intentionally left to the service layer (Python) so that
    the repository remains DB-agnostic (SQLite for tests, Postgres in prod).
    PostgreSQL-specific functions like DATE_TRUNC are NOT used here.

Import chain: repository → models, shared. No imports from service/router.
"""

from __future__ import annotations

from datetime import date, datetime, time as time_type
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from features.orders.models import DetallePedido, Pedido
from features.products.models import Producto
from features.users.models import Usuario


class MetricsRepository:
    """
    Read-only aggregation queries for admin metrics.

    Does NOT extend BaseRepository — there is no single "model" root,
    and no write operations are needed.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── helpers ─────────────────────────────────────────────────────────────

    def _date_to_datetime_range(
        self,
        desde: Optional[date],
        hasta: Optional[date],
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Convert optional date bounds to inclusive datetime bounds.

        desde → start of the day (00:00:00)
        hasta → end of the day (23:59:59.999999)
        """
        dt_desde = datetime.combine(desde, time_type.min) if desde else None
        dt_hasta = datetime.combine(hasta, time_type.max) if hasta else None
        return dt_desde, dt_hasta

    def _apply_date_filter(self, stmt, dt_desde, dt_hasta):
        """Apply optional date range filter on Pedido.creado_en."""
        if dt_desde is not None:
            stmt = stmt.where(Pedido.creado_en >= dt_desde)
        if dt_hasta is not None:
            stmt = stmt.where(Pedido.creado_en <= dt_hasta)
        return stmt

    # ── queries ──────────────────────────────────────────────────────────────

    def get_resumen_pedidos(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> Tuple[Decimal, int]:
        """
        Return (total_ventas, total_pedidos) for orders in the period.

        Excludes soft-deleted orders (eliminado_en IS NULL — BaseModel default).
        """
        dt_desde, dt_hasta = self._date_to_datetime_range(desde, hasta)

        stmt = select(
            func.coalesce(func.sum(Pedido.total), 0).label("total_ventas"),
            func.count(Pedido.id).label("total_pedidos"),
        ).where(Pedido.eliminado_en.is_(None))

        stmt = self._apply_date_filter(stmt, dt_desde, dt_hasta)

        row = self.session.execute(stmt).one()
        return Decimal(str(row.total_ventas)), int(row.total_pedidos)

    def get_total_usuarios(self) -> int:
        """Count active (non-soft-deleted) users."""
        stmt = select(func.count(Usuario.id)).where(
            Usuario.eliminado_en.is_(None)
        )
        return int(self.session.execute(stmt).scalar_one())

    def get_ventas_raw(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> List[Tuple[datetime, Decimal]]:
        """
        Return raw (creado_en, total) rows for all orders in the period.

        The service layer groups these by day/week/month (D2 — DB-agnostic).
        """
        dt_desde, dt_hasta = self._date_to_datetime_range(desde, hasta)

        stmt = select(Pedido.creado_en, Pedido.total).where(
            Pedido.eliminado_en.is_(None)
        )
        stmt = self._apply_date_filter(stmt, dt_desde, dt_hasta)
        stmt = stmt.order_by(Pedido.creado_en)

        rows = self.session.execute(stmt).all()
        return [(row.creado_en, Decimal(str(row.total))) for row in rows]

    def get_top_productos(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        top: int = 10,
    ) -> List[Tuple[int, str, int, Decimal]]:
        """
        Return top N products by total quantity sold.

        Returns list of (producto_id, nombre_snapshot, cantidad_total, ingreso_total).
        Joins DetallePedido with Pedido for date filtering.
        """
        dt_desde, dt_hasta = self._date_to_datetime_range(desde, hasta)

        stmt = (
            select(
                DetallePedido.producto_id,
                DetallePedido.nombre_snapshot,
                func.sum(DetallePedido.cantidad).label("cantidad_total"),
                func.sum(
                    DetallePedido.cantidad * DetallePedido.precio_snapshot
                ).label("ingreso_total"),
            )
            .join(Pedido, DetallePedido.pedido_id == Pedido.id)
            .join(Producto, DetallePedido.producto_id == Producto.id)
            .where(Pedido.eliminado_en.is_(None))
            .where(Producto.eliminado_en.is_(None))
            .group_by(DetallePedido.producto_id, DetallePedido.nombre_snapshot)
            .order_by(func.sum(DetallePedido.cantidad).desc())
            .limit(top)
        )

        if dt_desde is not None:
            stmt = stmt.where(Pedido.creado_en >= dt_desde)
        if dt_hasta is not None:
            stmt = stmt.where(Pedido.creado_en <= dt_hasta)

        rows = self.session.execute(stmt).all()
        return [
            (
                row.producto_id,
                row.nombre_snapshot,
                int(row.cantidad_total),
                Decimal(str(row.ingreso_total)),
            )
            for row in rows
        ]

    def get_pedidos_por_estado(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> List[Tuple[str, int]]:
        """
        Return (estado_codigo, count) pairs for all order states in the period.
        """
        dt_desde, dt_hasta = self._date_to_datetime_range(desde, hasta)

        stmt = (
            select(
                Pedido.estado_codigo,
                func.count(Pedido.id).label("cantidad"),
            )
            .where(Pedido.eliminado_en.is_(None))
            .group_by(Pedido.estado_codigo)
            .order_by(Pedido.estado_codigo)
        )
        stmt = self._apply_date_filter(stmt, dt_desde, dt_hasta)

        rows = self.session.execute(stmt).all()
        return [(row.estado_codigo, int(row.cantidad)) for row in rows]
