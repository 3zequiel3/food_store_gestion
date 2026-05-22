"""
Kitchen Display System (KDS) service.

GET /cocina/pedidos returns CONFIRMADO + EN_PREPARACION orders sorted by
kitchen entry time (creado_en of HistorialEstadoPedido where estado_nuevo_codigo = CONFIRMADO).

Phase 1 cutover: real-time broadcasting is now owned by features/websocket/.
- The asyncio queue, drain task, and publish_transition_event are removed.
- KDS receives events through the shared transport (kitchen:all topic via /ws).
- orders/service.py publishes via the EventPublisher port (no cocina import).

Phase 5 (P1.4 backend, D10): the kitchen payload now includes the full ingredient
list for each product (joining product_ingredients → ingredients) and resolves
personalizacion exclusion IDs to ingredient names.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from features.cocina.schemas import CocinaPedidoItem, CocinaPedidoResponse, IngredienteInfo
from features.orders.models import DetallePedido, HistorialEstadoPedido, Pedido
from features.products.models import Producto
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Item payload builder (D10 / P1.4 backend)
# ---------------------------------------------------------------------------


def _build_cocina_item(item: DetallePedido) -> CocinaPedidoItem:
    """
    Build a CocinaPedidoItem from a DetallePedido with its product pre-loaded.

    Design D10: eager-loads product.ingredientes (via the relationship defined
    in Producto.ingredientes → secondary product_ingredients → ingredients) to
    avoid N+1. Resolves personalizacion exclusion IDs to ingredient names.

    Parameters:
      item — a DetallePedido with item.producto.ingredientes already loaded
             (populated by selectinload in get_kitchen_orders).

    Returns a CocinaPedidoItem with:
      - ingredientes: full list with id, nombre, es_removible
      - exclusiones_nombres: ingredient names resolved from personalizacion IDs
    """
    # Build id→name map from the loaded ingredient list
    ingrediente_objs = list(item.producto.ingredientes)
    id_to_nombre: dict[int, str] = {ing.id: ing.nombre for ing in ingrediente_objs}

    ingredientes = [
        IngredienteInfo(id=ing.id, nombre=ing.nombre, es_removible=ing.es_removible)
        for ing in ingrediente_objs
    ]

    # Resolve exclusion IDs to names; unknown IDs are silently ignored (defensive)
    personalizacion: list[int] = item.personalizacion or []
    exclusiones_nombres = [
        id_to_nombre[ing_id]
        for ing_id in personalizacion
        if ing_id in id_to_nombre
    ]

    return CocinaPedidoItem(
        producto_id=item.producto_id,
        nombre_snapshot=item.nombre_snapshot,
        cantidad=item.cantidad,
        personalizacion=item.personalizacion,
        notas=None,
        ingredientes=ingredientes,
        exclusiones_nombres=exclusiones_nombres,
    )


# ---------------------------------------------------------------------------
# REST endpoint service
# ---------------------------------------------------------------------------


def get_kitchen_orders() -> list[CocinaPedidoResponse]:
    """
    Get all orders in CONFIRMADO + EN_PREPARACION, sorted by kitchen entry time.

    Kitchen entry time = the creado_en of the HistorialEstadoPedido row where
    estado_nuevo_codigo = CONFIRMADO (RN-CO02).

    Design D10 (P1.4 backend): eager-loads item.producto.ingredientes via
    selectinload to avoid N+1 when building the ingredient list per item.

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
            .options(
                # Eager-load items → producto → ingredientes to avoid N+1 (D10)
                selectinload(Pedido.items).selectinload(DetallePedido.producto).selectinload(Producto.ingredientes),
            )
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
            items=[_build_cocina_item(item) for item in pedido.items],
            notas=pedido.notas,
            cocina_entry_at=cocina_entry_at,
        )
        for pedido, cocina_entry_at in rows
    ]
