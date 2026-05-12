"""
Orders repository — data access for Pedido, DetallePedido, HistorialEstadoPedido.

D8: One unified OrderRepository handles all three entities (Pedido is the root
aggregate; DetallePedido and HistorialEstadoPedido have no identity outside of
a Pedido).

D4: get_producto_for_update uses .with_for_update() for pessimistic locking.
    In SQLite this is a no-op — concurrency tests must be marked pg_only.

Import chain (regla de oro): repository → models, shared.repository.
No imports from service, router, or FastAPI.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.features.catalog.models import EstadoPedido, FormaPago
from backend.features.orders.models import DetallePedido, HistorialEstadoPedido, Pedido
from backend.features.products.models import Producto
from backend.shared.repository import BaseRepository


class OrderRepository(BaseRepository[Pedido]):
    """
    Data access for the Orders aggregate root (Pedido + DetallePedido + HistorialEstadoPedido).

    Also provides read-only lookups into the product and payment method catalogs
    needed during the 9-step UoW for order creation (D8).
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    # ── Catalog lookups ──────────────────────────────────────────────────────

    def get_producto_for_update(self, producto_id: int) -> Optional[Producto]:
        """
        Fetch a product with a pessimistic lock (SELECT FOR UPDATE).

        D4: .with_for_update() ensures stock validation and order creation are
        serialized per product row under concurrency. In SQLite this is a no-op
        (SQLite doesn't support FOR UPDATE) — concurrency tests must be pg_only.

        Returns None if:
        - product doesn't exist, OR
        - product is soft-deleted (eliminado_en IS NOT NULL).
        """
        stmt = (
            select(Producto)
            .where(
                Producto.id == producto_id,
                Producto.eliminado_en.is_(None),
            )
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def find_forma_pago(self, codigo: str) -> Optional[FormaPago]:
        """
        Return a payment method only if it exists AND is enabled.

        Returns None if:
        - codigo doesn't exist in payment_methods, OR
        - habilitada=False (disabled by admin), OR
        - soft-deleted (eliminado_en IS NOT NULL).
        """
        stmt = (
            select(FormaPago)
            .where(
                FormaPago.codigo == codigo,
                FormaPago.habilitada.is_(True),
                FormaPago.eliminado_en.is_(None),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # ── Order creation ───────────────────────────────────────────────────────

    def create_pedido(
        self,
        user_id: int,
        direccion_id: Optional[int],
        direccion_snapshot: Optional[str],
        total: Decimal,
        costo_envio: Decimal,
        forma_pago_codigo: str,
        notas: Optional[str],
    ) -> Pedido:
        """
        Insert a new Pedido row and flush to obtain the generated id.

        estado_codigo is hardcoded to "PENDIENTE" — only the service can
        set the initial state (RN-PE06). The caller must commit via UoW.

        After flush, pedido.id is available for subsequent DetallePedido
        and HistorialEstadoPedido inserts (steps 7 and 8 of the 9-step UoW).
        """
        pedido = Pedido(
            user_id=user_id,
            direccion_entrega_id=direccion_id,
            direccion_snapshot=direccion_snapshot,
            total=total,
            costo_envio=costo_envio,
            forma_pago_codigo=forma_pago_codigo,
            estado_codigo="PENDIENTE",
            notas=notas,
        )
        self.session.add(pedido)
        self.session.flush()
        self.session.refresh(pedido)
        return pedido

    def create_detalle(
        self,
        pedido_id: int,
        producto: Producto,
        cantidad: int,
        personalizacion: Optional[list[int]],
    ) -> DetallePedido:
        """
        Insert a DetallePedido row with immutable snapshots.

        D8: snapshots (nombre_snapshot, precio_snapshot) are captured from the
        ORM instance, NOT from the request, so they cannot be tampered with
        and they remain stable even if the product is later edited.

        Flushes after add so the id is available if needed downstream.
        """
        detalle = DetallePedido(
            pedido_id=pedido_id,
            producto_id=producto.id,
            nombre_snapshot=producto.nombre,
            precio_snapshot=producto.precio,
            cantidad=cantidad,
            personalizacion=personalizacion,
        )
        self.session.add(detalle)
        self.session.flush()
        return detalle

    def create_historial_inicial(
        self,
        pedido_id: int,
        user_id: int,
    ) -> HistorialEstadoPedido:
        """
        Insert the first entry in order_state_history.

        RN-02, RN-PE06:
        - estado_anterior_codigo=None (no prior state — this is the creation event).
        - estado_nuevo_codigo="PENDIENTE" (always the initial state).
        - cambiado_por_id=user_id (the client who created the order).
        """
        historial = HistorialEstadoPedido(
            pedido_id=pedido_id,
            estado_anterior_codigo=None,
            estado_nuevo_codigo="PENDIENTE",
            cambiado_por_id=user_id,
        )
        self.session.add(historial)
        self.session.flush()
        return historial

    def create_historial_transicion(
        self,
        pedido_id: int,
        estado_anterior_codigo: str,
        estado_nuevo_codigo: str,
        actor_id: Optional[int],
    ) -> HistorialEstadoPedido:
        """
        Append a state transition entry to order_state_history.

        Used by OrderService.transicionar_estado() for system-triggered transitions
        (actor_id=None = SISTEMA) and future manual transitions (#16).
        """
        historial = HistorialEstadoPedido(
            pedido_id=pedido_id,
            estado_anterior_codigo=estado_anterior_codigo,
            estado_nuevo_codigo=estado_nuevo_codigo,
            cambiado_por_id=actor_id,
        )
        self.session.add(historial)
        self.session.flush()
        return historial

    def find_by_id(self, pedido_id: int) -> Optional[Pedido]:
        """Return a Pedido by id (no ownership check — for system transitions)."""
        stmt = select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.eliminado_en.is_(None),
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # ── Order retrieval (for future use in order-visualization-backend #17) ──

    def get_pedido_completo(
        self,
        pedido_id: int,
        user_id: int,
    ) -> Optional[Pedido]:
        """
        Fetch a Pedido with eager-loaded items and historial.

        Filters by user_id (ownership) and eliminado_en IS NULL (soft delete).
        Used by fixtures in tests and reserved for visualization endpoints (#17).
        """
        stmt = (
            select(Pedido)
            .options(
                selectinload(Pedido.items),
                selectinload(Pedido.historial),
            )
            .where(
                Pedido.id == pedido_id,
                Pedido.user_id == user_id,
                Pedido.eliminado_en.is_(None),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
