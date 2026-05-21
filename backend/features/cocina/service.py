"""
Kitchen Display System (KDS) service.

D6: GET /cocina/pedidos returns CONFIRMADO + EN_PREPARACION orders sorted by
kitchen entry time (creado_en of HistorialEstadoPedido where estado_nuevo_codigo = CONFIRMADO).

D5: Event broadcasting — after a state transition commits, publish a WebSocket event.
Uses an asyncio.Queue drained by a background task so the sync UoW commit is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from features.cocina.schemas import CocinaEvent, CocinaPedidoItem, CocinaPedidoResponse
from features.cocina.ws_manager import ws_manager
from features.orders.models import DetallePedido, HistorialEstadoPedido, Pedido
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Async event queue for post-commit broadcasts (D5)
#
# transicionar_estado is sync (runs in FastAPI's threadpool). We cannot await
# inside it. Instead, we put events into this queue (sync, non-blocking) and
# an async background task drains it and calls ws_manager.broadcast().
# ---------------------------------------------------------------------------

_event_queue: Optional[asyncio.Queue] = None
_drain_task: Optional[asyncio.Task] = None


def get_event_queue() -> asyncio.Queue:
    """Get or create the singleton event queue."""
    global _event_queue
    if _event_queue is None:
        _event_queue = asyncio.Queue(maxsize=100)
    return _event_queue


def start_drain_task(loop: asyncio.AbstractEventLoop) -> None:
    """
    Start the background task that drains the event queue and broadcasts.

    Called from the lifespan startup. Safe to call multiple times (idempotent).
    """
    global _drain_task
    if _drain_task is not None and not _drain_task.done():
        return  # Already running

    queue = get_event_queue()
    _drain_task = loop.create_task(_drain_loop(queue))
    logger.info("KDS event drain task started")


async def _drain_loop(queue: asyncio.Queue) -> None:
    """Continuously drain the event queue and broadcast each event."""
    while True:
        try:
            event = await queue.get()
            await ws_manager.broadcast(event)
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("KDS drain loop error — continuing")


def publish_kitchen_event(event: dict) -> None:
    """
    Enqueue a kitchen event for broadcast (best-effort, non-blocking).

    Called from sync code (transicionar_estado) after UoW commit.
    Uses run_coroutine_threadsafe to put the event into the async queue.
    If the event loop is not available or the queue is full, silently discard.
    """
    try:
        loop = asyncio.get_event_loop()
        queue = get_event_queue()
        # run_coroutine_threadsafe is safe even if called from the same thread
        # (it schedules the coroutine on the loop). If the loop is closed or
        # not running, it raises — we catch and discard (best-effort).
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)
    except Exception:
        logger.debug("KDS publish failed (best-effort, silently discarded)")


# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

_STATE_TO_EVENT: dict[str, str] = {
    "CONFIRMADO": "pedido_confirmado",
    "EN_PREPARACION": "pedido_en_preparacion",
    "TERMINADO": "pedido_terminado",
    "CANCELADO": "pedido_cancelado",
    "CANCELADO_ADMIN": "pedido_cancelado",
    "CANCELADO_CLIENTE": "pedido_cancelado",
}


def _state_to_event_type(estado_nuevo: str) -> Optional[str]:
    """Map a state code to the corresponding WebSocket event type."""
    return _STATE_TO_EVENT.get(estado_nuevo)


def _build_event_payload(pedido: Pedido, cocina_entry_at) -> dict:
    """Build the minimal event payload from a Pedido ORM instance."""
    return {
        "id": pedido.id,
        "estado": pedido.estado_codigo,
        "items": [
            {
                "producto_id": item.producto_id,
                "nombre_snapshot": item.nombre_snapshot,
                "cantidad": item.cantidad,
                "personalizacion": item.personalizacion,
                "notas": None,
            }
            for item in pedido.items
        ],
        "notas": pedido.notas,
        "cocina_entry_at": cocina_entry_at,
    }


# ---------------------------------------------------------------------------
# Public API — called after UoW commit in transicionar_estado
# ---------------------------------------------------------------------------

def publish_transition_event(pedido_id: int, estado_nuevo: str) -> None:
    """
    Publish a WebSocket event after a state transition commits.

    Best-effort: if the event type doesn't map to a kitchen event, or if
    broadcasting fails, silently discard.

    Called from orders/service.py:transicionar_estado AFTER the UoW commit.
    """
    event_type = _state_to_event_type(estado_nuevo)
    if event_type is None:
        return  # Not a kitchen-relevant state

    # We need the order snapshot. Open a read-only session to fetch it.
    # This is a separate query AFTER commit — if it fails, we discard.
    try:
        from shared.database import get_session_factory

        session = get_session_factory()()
        try:
            stmt = (
                select(Pedido)
                .options(selectinload(Pedido.items))
                .where(Pedido.id == pedido_id)
            )
            pedido = session.execute(stmt).scalar_one_or_none()
            if pedido is None:
                return

            # Find the kitchen entry time (transition to CONFIRMADO)
            hist_stmt = (
                select(HistorialEstadoPedido.creado_en)
                .where(
                    HistorialEstadoPedido.pedido_id == pedido_id,
                    HistorialEstadoPedido.estado_nuevo_codigo == "CONFIRMADO",
                )
                .order_by(HistorialEstadoPedido.creado_en.asc())
                .limit(1)
            )
            cocina_entry_at = session.execute(hist_stmt).scalar_one_or_none()

            payload = _build_event_payload(pedido, cocina_entry_at or pedido.creado_en)
            event = {"type": event_type, "payload": payload}
            publish_kitchen_event(event)
        finally:
            session.close()
    except Exception:
        logger.debug("KDS publish_transition_event failed (best-effort, silently discarded)")


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
