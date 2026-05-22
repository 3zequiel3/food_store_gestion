"""
Kitchen Display System (KDS) service.

GET /cocina/pedidos returns CONFIRMADO + EN_PREPARACION orders sorted by
kitchen entry time (creado_en of HistorialEstadoPedido where estado_nuevo_codigo = CONFIRMADO).

Phase 1 cutover: real-time broadcasting is now owned by features/websocket/.
- The asyncio queue, drain task, and publish_transition_event are removed.
- KDS receives events through the shared transport (kitchen:all topic via /ws).
- orders/service.py publishes via the EventPublisher port (no cocina import).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from features.cocina.schemas import CocinaPedidoItem, CocinaPedidoResponse
from features.orders.models import HistorialEstadoPedido, Pedido
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REST endpoint service
# ---------------------------------------------------------------------------


def get_kitchen_orders() -> list[CocinaPedidoResponse]:
    """
    Get all orders in CONFIRMADO + EN_PREPARACION, sorted by kitchen entry time.

    Kitchen entry time = the creado_en of the HistorialEstadoPedido row where
    estado_nuevo_codigo = CONFIRMADO (RN-CO02).

    Returns a list of CocinaPedidoResponse sorted oldest-first (most urgent first).
    """
    with UnitOfWork() as uow:
        # Subquery: get the kitchen entry time for each order
        # (the creado_en of the first transition to CONFIRMADO)
        from sqlalchemy import func as sa_func

        kitchen_entry_subq = (
            select(
                HistorialEstadoPedido.pedido_id,
                sa_func.min(HistorialEstadoPedido.creado_en).label("cocina_entry_at"),
            )
            .where(HistorialEstadoPedido.estado_nuevo_codigo == "CONFIRMADO")
            .group_by(HistorialEstadoPedido.pedido_id)
            .subquery()
        )

        stmt = (
            select(Pedido, kitchen_entry_subq.c.cocina_entry_at)
            .options(selectinload(Pedido.items))
            .join(
                kitchen_entry_subq,
                Pedido.id == kitchen_entry_subq.c.pedido_id,
            )
            .where(
                Pedido.estado_codigo.in_(["CONFIRMADO", "EN_PREPARACION"]),
                Pedido.eliminado_en.is_(None),
            )
            .order_by(kitchen_entry_subq.c.cocina_entry_at.asc())
        )

        rows = uow.session.execute(stmt).all()

    return [
        CocinaPedidoResponse(
            id=pedido.id,
            estado=pedido.estado_codigo,
            items=[
                CocinaPedidoItem(
                    producto_id=item.producto_id,
                    nombre_snapshot=item.nombre_snapshot,
                    cantidad=item.cantidad,
                    personalizacion=item.personalizacion,
                    notas=None,
                )
                for item in pedido.items
            ],
            notas=pedido.notas,
            cocina_entry_at=cocina_entry_at,
        )
        for pedido, cocina_entry_at in rows
    ]
