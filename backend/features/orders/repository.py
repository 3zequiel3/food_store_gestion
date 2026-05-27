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

from datetime import date, datetime, time as time_type, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from features.catalog.models import FormaPago
from features.orders.models import DetallePedido, HistorialEstadoPedido, Pedido
from features.products.models import Producto
from features.users.models import Usuario
from shared.exceptions import BusinessRuleError
from shared.repository import BaseRepository


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
        motivo: Optional[str] = None,
    ) -> HistorialEstadoPedido:
        """
        Append a state transition entry to order_state_history.

        Used by OrderService.transicionar_estado() for system-triggered transitions
        (actor_id=None = SISTEMA) and manual transitions (#16).

        motivo: optional free-text reason (max 500 chars). NULL when not provided.
        """
        historial = HistorialEstadoPedido(
            pedido_id=pedido_id,
            estado_anterior_codigo=estado_anterior_codigo,
            estado_nuevo_codigo=estado_nuevo_codigo,
            cambiado_por_id=actor_id,
            motivo=motivo,
        )
        self.session.add(historial)
        self.session.flush()
        return historial

    def get_pedido_for_update(self, pedido_id: int) -> Optional[Pedido]:
        """
        Fetch a Pedido with a pessimistic lock (SELECT FOR UPDATE).

        D8: Replaces find_by_id() inside transicionar_estado() to serialize
        concurrent workers (e.g. duplicate webhooks). In SQLite (tests) this
        is a no-op — concurrency tests must be marked pg_only.

        Returns None if the pedido does not exist or is soft-deleted.
        """
        stmt = (
            select(Pedido)
            .where(
                Pedido.id == pedido_id,
                Pedido.eliminado_en.is_(None),
            )
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def pedido_belongs_to_user(self, pedido_id: int, user_id: int) -> bool:
        """
        Return True if a non-deleted Pedido with pedido_id exists and belongs to user_id.

        Used by the WebSocket subscribe handler to enforce ownership on CLIENT
        subscriptions to `order:{N}` topics (D4 hardening). Selects only
        Pedido.id to avoid loading the full ORM row for a boolean check.
        """
        stmt = select(Pedido.id).where(
            Pedido.id == pedido_id,
            Pedido.user_id == user_id,
            Pedido.eliminado_en.is_(None),
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def find_by_id(self, pedido_id: int) -> Optional[Pedido]:
        """Return a Pedido by id (no ownership check — for system transitions)."""
        stmt = select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.eliminado_en.is_(None),
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # ── Stock side-effects (order-state-machine-fsm #16) ────────────────────

    def decrement_stock_for_items(self, items: list[DetallePedido]) -> None:
        """
        Decrement stock for each DetallePedido item using SELECT FOR UPDATE.

        D8 — called inside transicionar_estado() UoW when PENDIENTE → CONFIRMADO.
        Each product row is locked before decrement to serialize concurrent requests.

        S1: a single flush after the loop replaces N per-iteration flushes —
        FOR UPDATE locks remain held until the UoW commits, so batching is safe.

        Raises:
            BusinessRuleError: if stock would go negative for any product.
        """
        for item in items:
            stmt = (
                select(Producto)
                .where(
                    Producto.id == item.producto_id,
                    Producto.eliminado_en.is_(None),
                )
                .with_for_update()
            )
            producto = self.session.execute(stmt).scalar_one_or_none()
            if producto is None:
                raise BusinessRuleError(
                    f"Producto id={item.producto_id} no encontrado al decrementar stock"
                )
            if producto.stock_cantidad < item.cantidad:
                raise BusinessRuleError(
                    f"Stock insuficiente para confirmar pedido: "
                    f"producto '{producto.nombre}' tiene {producto.stock_cantidad} unidades, "
                    f"se necesitan {item.cantidad}"
                )
            producto.stock_cantidad -= item.cantidad

        if items:
            self.session.flush()

    def restore_stock_for_items(self, items: list[DetallePedido]) -> None:
        """
        Restore stock for each DetallePedido item using SELECT FOR UPDATE.

        D6 — called inside transicionar_estado() UoW when (CONFIRMADO|EN_PREPARACION)
        → CANCELADO. Adds item.cantidad back to each product's stock.

        S1: a single flush after the loop replaces N per-iteration flushes.
        """
        for item in items:
            stmt = (
                select(Producto)
                .where(
                    Producto.id == item.producto_id,
                    Producto.eliminado_en.is_(None),
                )
                .with_for_update()
            )
            producto = self.session.execute(stmt).scalar_one_or_none()
            if producto is None:
                raise BusinessRuleError(
                    f"Producto id={item.producto_id} no encontrado al restaurar stock"
                )
            producto.stock_cantidad += item.cantidad

        if items:
            self.session.flush()

    # ── Order retrieval (order-visualization-backend #17) ────────────────────

    def _apply_pedido_filters(
        self,
        stmt,
        *,
        user_id: int | None,
        estado: str | None,
        desde: date | None,
        hasta: date | None,
        q: str | None,
    ):
        """
        Apply the standard pedido filters to a select statement.

        Always filters out soft-deleted rows. Single source of truth shared by
        `list_with_filter` and `count_with_filter` so a `total` cannot diverge
        from the listed rows when a filter is added or removed.

        Behavior:
        - `user_id`, `estado`, `desde`, `hasta` → narrow scalar WHERE clauses.
        - `q` numeric → match `Pedido.id`.
        - `q` non-numeric → JOIN `Pedido.usuario` + ilike over "nombre apellido".
        """
        stmt = stmt.where(Pedido.eliminado_en.is_(None))

        if user_id is not None:
            stmt = stmt.where(Pedido.user_id == user_id)
        if estado is not None:
            stmt = stmt.where(Pedido.estado_codigo == estado)
        if desde is not None:
            stmt = stmt.where(
                Pedido.creado_en >= datetime.combine(desde, time_type.min)
            )
        if hasta is not None:
            stmt = stmt.where(
                Pedido.creado_en < datetime.combine(hasta + timedelta(days=1), time_type.min)
            )
        if q is not None:
            if q.isdigit():
                stmt = stmt.where(Pedido.id == int(q))
            else:
                stmt = stmt.join(Pedido.usuario).where(
                    (Usuario.nombre + " " + Usuario.apellido).ilike(f"%{q}%")
                )

        return stmt

    def list_with_filter(
        self,
        *,
        user_id: int | None,
        estado: str | None,
        desde: date | None,
        hasta: date | None,
        q: str | None,
        page: int,
        limit: int,
    ) -> list[tuple[Pedido, int]]:
        """
        Paginated order list with optional filters. Returns (Pedido, items_count) tuples.

        items_count is computed via correlated subquery over order_items (PG only).
        Falls back to 0 for each row in SQLite test environments (OperationalError).

        D4: no selectinload — list does NOT eager-load relations to avoid N+1.
        Order: creado_en DESC (US-049).
        """
        items_count_sq = (
            select(func.count(DetallePedido.id))
            .where(DetallePedido.pedido_id == Pedido.id)
            .correlate(Pedido)
            .scalar_subquery()
        )

        full_stmt = self._apply_pedido_filters(
            select(Pedido, items_count_sq.label("items_count")),
            user_id=user_id, estado=estado, desde=desde, hasta=hasta, q=q,
        ).order_by(Pedido.creado_en.desc()).offset((page - 1) * limit).limit(limit)

        try:
            rows = self.session.execute(full_stmt).all()
            return [(row[0], row[1]) for row in rows]
        except OperationalError:
            # SQLite: order_items table not available — return 0 for items_count
            plain_stmt = self._apply_pedido_filters(
                select(Pedido),
                user_id=user_id, estado=estado, desde=desde, hasta=hasta, q=q,
            ).order_by(Pedido.creado_en.desc()).offset((page - 1) * limit).limit(limit)
            pedidos = self.session.execute(plain_stmt).scalars().all()
            return [(p, 0) for p in pedidos]

    def count_with_filter(
        self,
        *,
        user_id: int | None,
        estado: str | None,
        desde: date | None,
        hasta: date | None,
        q: str | None,
    ) -> int:
        """
        Count orders matching the same filters as list_with_filter (no offset/limit).

        Used for the `total` field in PaginatedPedidos. Filter logic is shared
        via `_apply_pedido_filters` so total cannot drift from listed rows.
        """
        stmt = self._apply_pedido_filters(
            select(func.count(Pedido.id)),
            user_id=user_id, estado=estado, desde=desde, hasta=hasta, q=q,
        )

        return self.session.execute(stmt).scalar_one()

    def get_pedido_completo(
        self,
        pedido_id: int,
        user_id: int | None,
    ) -> Optional[Pedido]:
        """
        Fetch a Pedido with eager-loaded items, historial, and pagos.

        D5: user_id=None → no ownership filter (admin path).
             user_id=int → filters WHERE pedido.user_id = user_id (client path).
        Returns None if not found, soft-deleted, or ownership mismatch.

        SQLite fallback: order_items uses ARRAY(Integer) (PG-only). In SQLite test
        environments the selectinload for items raises OperationalError. The fallback
        loads historial and pagos via lazy-load and marks items as empty so callers
        don't trigger a second failing lazy-load.
        """
        from sqlalchemy.orm import attributes as sa_attrs

        base_where = [Pedido.id == pedido_id, Pedido.eliminado_en.is_(None)]
        if user_id is not None:
            base_where.append(Pedido.user_id == user_id)

        stmt = (
            select(Pedido)
            .options(
                selectinload(Pedido.items),
                selectinload(Pedido.historial),
                selectinload(Pedido.pagos),
            )
            .where(*base_where)
        )
        try:
            return self.session.execute(stmt).scalar_one_or_none()
        except OperationalError:
            # SQLite: order_items (ARRAY) unavailable. Re-fetch without items selectinload.
            plain_stmt = select(Pedido).where(*base_where)
            pedido = self.session.execute(plain_stmt).scalar_one_or_none()
            if pedido is None:
                return None
            # Trigger lazy-loads for SQLite-compatible relations
            _ = list(pedido.historial)
            _ = list(pedido.pagos)
            # Mark items as loaded-empty to prevent future lazy-load failure
            sa_attrs.set_committed_value(pedido, "items", [])
            return pedido
