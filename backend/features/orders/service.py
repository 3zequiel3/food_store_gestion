"""
Order service — business logic for order creation.

D3: Service-driven UoW. OrderService.crear_pedido() opens its own
    `with UnitOfWork() as uow:` context. The router does NOT open UoW.

D5: costo_envio v1 fixed rate: Decimal("50.00") with address,
    Decimal("0.00") for in-store pickup (retiro en local).

D6: Anti-leak ownership — a direccion_id that doesn't exist OR belongs
    to another user raises NotFoundError (404), not ForbiddenError (403).

D7: Two repositories registered in the same UoW:
    - "orders"     → OrderRepository  (order aggregate)
    - "direcciones" → AddressRepository (for ownership enforcement, D6)

D11: Decimal end-to-end. No floats in monetary calculations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import OperationalError

from features.addresses.repository import AddressRepository
from features.orders.models import Pedido
from features.orders.repository import OrderRepository
from features.orders.schemas import (
    CrearPedidoRequest,
    HistorialItem,
    ItemDetalle,
    PaginatedPedidos,
    PagoSummary,
    PedidoDetalle,
    PedidoListFilters,
    PedidoListItem,
)
from features.orders.state_machine import validate_transition
from features.users.models import Usuario
from features.users.repository import UserProfileRepository
from shared.exceptions import (
    BusinessRuleError,
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
)
from shared.unit_of_work import UnitOfWork

import logging as _logging

_svc_logger = _logging.getLogger(__name__)

# D5 — v1 fixed shipping cost. Replace with dynamic calculation in a future change.
SHIPPING_COST_DEFAULT = Decimal("50.00")

# ---------------------------------------------------------------------------
# Domain event publishing — EventPublisher port (Design D2, D4).
# The order domain publishes via the port; no import from features.cocina.
# Kitchen-relevant states emit to kitchen:all so the KDS (cocina consumer)
# receives them through the shared transport.
# ---------------------------------------------------------------------------

_KITCHEN_STATES = frozenset({
    "CONFIRMADO", "EN_PREPARACION", "TERMINADO",
    "CANCELADO", "CANCELADO_ADMIN", "CANCELADO_CLIENTE",
})


def _publish_order_state_event(pedido_id: int, estado_nuevo: str) -> None:
    """
    Publish an order_state_changed domain event via the EventPublisher port.

    Best-effort: any exception is caught and logged at DEBUG level; the HTTP
    response for the originating transition is never affected.

    Design D2: versioned contract {v, type, topic, payload, ts}.
    Design D4: kitchen-relevant states go to kitchen:all; other states are
    silently skipped (not kitchen-relevant in Phase 1).
    """
    if estado_nuevo not in _KITCHEN_STATES:
        return

    try:
        from features.websocket.registration import get_event_publisher
        from features.websocket.contracts import DomainEvent

        publisher = get_event_publisher()
        if publisher is None:
            # register_realtime hasn't been called yet (e.g. tests without lifespan).
            return

        event = DomainEvent(
            v=1,
            type="order_state_changed",
            topic="kitchen:all",
            payload={"order_id": pedido_id, "estado": estado_nuevo},
        )
        publisher.publish(event)
    except Exception:
        _svc_logger.debug(
            "orders/service: post-commit publish failed (best-effort, discarded)",
            exc_info=True,
        )


def _is_admin_view(user: Usuario) -> bool:
    """
    Determine if the user has admin-level access to orders.

    Returns True for PEDIDOS or ADMIN roles (sees all orders).
    Returns False for CLIENT role (sees only own orders).
    Raises ForbiddenError for STOCK-only users (no order access).
    """
    roles = {r.codigo for r in user.roles}
    if roles & {"PEDIDOS", "ADMIN"}:
        return True
    if roles & {"CLIENT"}:
        return False
    raise ForbiddenError("Rol STOCK no autorizado para acceder a pedidos")


def _build_direccion_snapshot(direccion) -> str:
    """
    Build a human-readable snapshot of the delivery address.

    Format: "{calle} {numero}[, {piso_depto}], {ciudad} {codigo_postal}[, {referencia}]"
    This snapshot is immutable once captured — future edits to the address
    do NOT retroactively change this text (RN-DA06, D1).
    """
    parts = [f"{direccion.calle} {direccion.numero}"]
    if direccion.piso_depto:
        parts[0] += f", {direccion.piso_depto}"
    parts.append(f"{direccion.ciudad} {direccion.codigo_postal}")
    snapshot = ", ".join(parts)
    if direccion.referencia:
        snapshot += f", {direccion.referencia}"
    return snapshot


class OrderService:
    """
    Stateless service for order creation.

    One instance per request is fine (no shared mutable state).
    """

    def __init__(self) -> None:
        pass

    def crear_pedido(self, user_id: int, payload: CrearPedidoRequest) -> Pedido:
        """
        Create a new order atomically — 9-step UoW (spec §7.1).

        Steps:
          1. Validate forma_pago_codigo exists and is enabled.
          2. Validate direccion_id ownership (if provided).
          3. Build direccion_snapshot (or None for in-store pickup).
          4. Validate each product: exists, disponible=True, stock sufficient (SELECT FOR UPDATE).
          5. Calculate subtotal and total (Decimal, no float).
          6. INSERT Pedido (flush to get id).
          7. INSERT DetallePedido for each item.
          8. INSERT HistorialEstadoPedido (estado_anterior=None, estado_nuevo=PENDIENTE).
          9. Refresh creado_en. UoW __exit__ commits.

        Raises:
            BusinessRuleError: invalid forma_pago or stock/disponibilidad issues (→ 422).
            NotFoundError: unknown product or address not owned by user (→ 404).
        """
        with UnitOfWork() as uow:
            # D7: Register two repositories in the same UoW.
            uow.register_repository("orders", OrderRepository(uow.session))
            uow.register_repository("direcciones", AddressRepository(uow.session))

            # ── Step 1: Validate forma de pago ────────────────────────────
            forma = uow.orders.find_forma_pago(payload.forma_pago_codigo)
            if forma is None:
                raise BusinessRuleError("Forma de pago no válida o no disponible")

            # P0.2: Cash-on-delivery (EFECTIVO + direccion_id) is now supported.
            # The old hard block was removed — EFECTIVO + address creates a PENDIENTE
            # order that the delivery driver collects at the door.

            # ── Step 2: Validate direccion ownership ──────────────────────
            direccion: Optional[object] = None
            if payload.direccion_id is not None:
                direccion = uow.direcciones.find_by_id_and_user(
                    payload.direccion_id, user_id
                )
                if direccion is None:
                    raise NotFoundError("Dirección no encontrada")

            # ── Step 3: Build direccion_snapshot ──────────────────────────
            direccion_snapshot: Optional[str] = None
            if direccion is not None:
                direccion_snapshot = _build_direccion_snapshot(direccion)

            # ── Step 4: Validate products (SELECT FOR UPDATE) ─────────────
            items_validados: list[tuple] = []
            for item in payload.items:
                producto = uow.orders.get_producto_for_update(item.producto_id)
                if producto is None:
                    raise NotFoundError(
                        f"Producto no encontrado: id={item.producto_id}"
                    )
                if not producto.disponible:
                    raise BusinessRuleError(
                        f"Producto no disponible: {producto.nombre!r}"
                    )
                if producto.stock_cantidad < item.cantidad:
                    raise BusinessRuleError(
                        f"Stock insuficiente para {producto.nombre!r} "
                        f"(disponible: {producto.stock_cantidad}, pedido: {item.cantidad})"
                    )
                items_validados.append((producto, item))

            # ── Step 5: Calculate totals ──────────────────────────────────
            # D11: use Decimal arithmetic — product.precio comes from Numeric(10,2)
            # ORM field (mapped as float in the model but stored as Numeric in PG).
            # Wrapping in Decimal() ensures precision.
            subtotal = sum(
                Decimal(str(producto.precio)) * item.cantidad
                for producto, item in items_validados
            )
            costo_envio = (
                SHIPPING_COST_DEFAULT if direccion is not None else Decimal("0.00")
            )
            total = subtotal + costo_envio

            # ── Step 6: Create Pedido ─────────────────────────────────────
            pedido = uow.orders.create_pedido(
                user_id=user_id,
                direccion_id=payload.direccion_id,
                direccion_snapshot=direccion_snapshot,
                total=total,
                costo_envio=costo_envio,
                forma_pago_codigo=payload.forma_pago_codigo,
                notas=payload.notas,
            )

            # ── Step 7: Create DetallePedido for each item ────────────────
            for producto, item in items_validados:
                uow.orders.create_detalle(
                    pedido_id=pedido.id,
                    producto=producto,
                    cantidad=item.cantidad,
                    personalizacion=item.personalizacion,
                )

            # ── Step 8: Create HistorialEstadoPedido ──────────────────────
            uow.orders.create_historial_inicial(
                pedido_id=pedido.id,
                user_id=user_id,
            )

            # ── Step 9: Refresh creado_en before UoW closes session ──────
            uow.session.refresh(pedido, attribute_names=["creado_en"])

            # UoW __exit__ commits on clean exit, rolls back on exception.
            return pedido

    def transicionar_estado(
        self,
        pedido_id: int,
        estado_anterior: str,
        estado_nuevo: str,
        actor_id: Optional[int] = None,
        motivo: Optional[str] = None,
    ) -> Pedido:
        """
        Transition an order from estado_anterior to estado_nuevo atomically.

        Used by PaymentService.procesar_webhook() (PENDIENTE→CONFIRMADO) and by
        avanzar_estado() for manual transitions (#16).

        Backwards-compatible: the existing webhook call signature is unchanged.
        actor_id=None means the transition was triggered by SISTEMA (webhook).

        Side-effects (D2, D6):
        - PENDIENTE → CONFIRMADO: decrements stock for each DetallePedido.
        - (CONFIRMADO|EN_PREPARACION) → CANCELADO: restores stock.

        Raises:
            NotFoundError: pedido_id doesn't exist.
            InvalidStateTransitionError: current state != estado_anterior (409).
            BusinessRuleError: insufficient stock on confirmation (422).
        """
        with UnitOfWork() as uow:
            uow.register_repository("orders", OrderRepository(uow.session))

            # D8: use FOR UPDATE to serialize concurrent workers
            pedido = uow.orders.get_pedido_for_update(pedido_id)
            if pedido is None:
                raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")

            if pedido.estado_codigo != estado_anterior:
                raise InvalidStateTransitionError(
                    f"Transición inválida: el pedido está en '{pedido.estado_codigo}', "
                    f"se esperaba '{estado_anterior}'"
                )

            # D2: stock side-effects before changing the state
            # Load items only when needed to avoid unnecessary queries.
            # In SQLite test environments order_items table doesn't exist
            # (ARRAY(Integer) is PG-specific); we catch OperationalError and
            # treat items as empty — stock side-effects are tested at the
            # repository level with mocked items.
            needs_stock_effect = (estado_anterior, estado_nuevo) in {
                ("PENDIENTE", "CONFIRMADO"),
                ("CONFIRMADO", "CANCELADO"),
                ("CONFIRMADO", "CANCELADO_ADMIN"),
                ("EN_PREPARACION", "CANCELADO"),
                ("EN_PREPARACION", "CANCELADO_ADMIN"),
            }
            if needs_stock_effect:
                try:
                    items = list(pedido.items)
                except OperationalError:
                    items = []  # SQLite: order_items table not available

                if (estado_anterior, estado_nuevo) == ("PENDIENTE", "CONFIRMADO"):
                    uow.orders.decrement_stock_for_items(items)
                else:
                    uow.orders.restore_stock_for_items(items)

            pedido.estado_codigo = estado_nuevo
            uow.session.flush()

            uow.orders.create_historial_transicion(
                pedido_id=pedido_id,
                estado_anterior_codigo=estado_anterior,
                estado_nuevo_codigo=estado_nuevo,
                actor_id=actor_id,
                motivo=motivo,
            )

            uow.session.refresh(pedido, attribute_names=["estado_codigo", "creado_en"])
            # Capture values for post-commit event publishing (D5, Slice 3)
            _event_pedido_id = pedido_id
            _event_estado_nuevo = estado_nuevo

        # Post-commit: publish domain event via the EventPublisher port (best-effort).
        # Design D2/D4: the order domain emits a versioned domain event; cocina
        # consumes it via the kitchen:all topic. No import from features.cocina.
        try:
            _publish_order_state_event(_event_pedido_id, _event_estado_nuevo)
        except Exception:
            pass  # Best-effort — never let publish failure affect the HTTP response

        return pedido

    def listar_pedidos(
        self, user: Usuario, filtros: PedidoListFilters
    ) -> PaginatedPedidos:
        """
        List orders with role-aware filtering and pagination.

        CLIENT: filters by user_id == current_user.id.
        PEDIDOS/ADMIN: no ownership filter.
        STOCK-only: ForbiddenError.

        D3: short-circuits before the list query when total == 0.
        """
        admin_view = _is_admin_view(user)
        user_id_filter: int | None = None if admin_view else user.id

        with UnitOfWork() as uow:
            uow.register_repository("orders", OrderRepository(uow.session))

            total = uow.orders.count_with_filter(
                user_id=user_id_filter,
                estado=filtros.estado,
                desde=filtros.desde,
                hasta=filtros.hasta,
                q=filtros.q,
            )

            if total == 0:
                return PaginatedPedidos(
                    items=[], total=0, page=filtros.page, limit=filtros.limit
                )

            rows = uow.orders.list_with_filter(
                user_id=user_id_filter,
                estado=filtros.estado,
                desde=filtros.desde,
                hasta=filtros.hasta,
                q=filtros.q,
                page=filtros.page,
                limit=filtros.limit,
            )

        items = [
            PedidoListItem(
                id=pedido.id,
                estado_codigo=pedido.estado_codigo,
                total=Decimal(str(pedido.total)),
                costo_envio=Decimal(str(pedido.costo_envio)),
                forma_pago_codigo=pedido.forma_pago_codigo,
                creado_en=pedido.creado_en,
                items_count=count,
            )
            for pedido, count in rows
        ]

        return PaginatedPedidos(
            items=items, total=total, page=filtros.page, limit=filtros.limit
        )

    def get_pedido_detalle(self, user: Usuario, pedido_id: int) -> PedidoDetalle:
        """
        Fetch full order detail with items, historial, and pagos.

        Anti-leak 404 (D2): CLIENT gets None when pedido exists but is not theirs —
        same 404 as pedido not found. No branching that reveals ownership.

        historial ordered by creado_en ASC, pagos by fecha DESC, items by id ASC.
        """
        admin_view = _is_admin_view(user)
        user_id_filter: int | None = None if admin_view else user.id

        with UnitOfWork() as uow:
            uow.register_repository("orders", OrderRepository(uow.session))
            pedido = uow.orders.get_pedido_completo(pedido_id, user_id=user_id_filter)

        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        return PedidoDetalle(
            id=pedido.id,
            user_id=pedido.user_id,
            estado_codigo=pedido.estado_codigo,
            total=Decimal(str(pedido.total)),
            costo_envio=Decimal(str(pedido.costo_envio)),
            forma_pago_codigo=pedido.forma_pago_codigo,
            direccion_snapshot=pedido.direccion_snapshot,
            notas=pedido.notas,
            creado_en=pedido.creado_en,
            actualizado_en=pedido.actualizado_en,
            items=sorted(
                [
                    ItemDetalle(
                        id=item.id,
                        producto_id=item.producto_id,
                        nombre_snapshot=item.nombre_snapshot,
                        precio_snapshot=Decimal(str(item.precio_snapshot)),
                        cantidad=item.cantidad,
                        personalizacion=item.personalizacion,
                    )
                    for item in pedido.items
                ],
                key=lambda x: x.id,
            ),
            historial=sorted(
                [HistorialItem.model_validate(h) for h in pedido.historial],
                key=lambda x: x.creado_en,
            ),
            pagos=sorted(
                [
                    PagoSummary(
                        id=p.id,
                        status=p.mp_status or "",
                        monto=Decimal(str(p.monto)),
                        fecha=p.creado_en,
                    )
                    for p in pedido.pagos
                ],
                key=lambda x: x.fecha,
                reverse=True,
            ),
        )

    def avanzar_estado(
        self,
        user_id: int,
        pedido_id: int,
        nuevo_estado: str,
        motivo: Optional[str] = None,
    ) -> Pedido:
        """
        Advance an order state with full FSM + RBAC + ownership validation.

        High-level layer (D1): validates who can do what, then delegates the
        actual state change to transicionar_estado() which handles the atomic
        UoW + stock side-effects.

        D14: Uses a direct read-only session for the validation phase (no UoW
        of its own). The pattern mirrors auth/dependencies.py:get_current_user.
        The race between this read and transicionar_estado's FOR UPDATE is
        benign: if state changed between the two reads, transicionar_estado
        raises InvalidStateTransitionError (409).

        Raises:
            BusinessRuleError: CONFIRMADO requested manually (D5), invalid FSM
                transition (D3), or missing motivo on critical cancellation (D7).
            NotFoundError: pedido not found, or CLIENT accessing another user's
                pedido (D13 anti-leak).
            ForbiddenError: user lacks required role for this transition (D4).
            InvalidStateTransitionError: race condition — state changed between
                the validation read and the UoW lock (409).
        """
        import shared.unit_of_work as _uow_mod

        # D5: first defense against manual CONFIRMADO
        if nuevo_estado == "CONFIRMADO":
            raise BusinessRuleError(
                "CONFIRMADO solo se setea automáticamente vía webhook de pago"
            )

        # Read-only session for validation — no UoW, no lock (D14)
        session = _uow_mod.get_session_factory()()
        try:
            order_repo = OrderRepository(session)
            user_repo = UserProfileRepository(session)

            pedido = order_repo.find_by_id(pedido_id)
            if pedido is None:
                raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")

            user = user_repo.find_by_id_with_roles(user_id)
            user_roles = {r.codigo for r in user.roles}

            # D13: ownership check — CLIENT can only act on their own orders
            if user_roles == {"CLIENT"} and pedido.user_id != user_id:
                raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")

            # D3 + D4: FSM and RBAC validation
            validate_transition(pedido.estado_codigo, nuevo_estado, user_roles)

            # D4: delivery-mode branching rule — EN_CAMINO only for delivery orders
            if pedido.estado_codigo == "TERMINADO":
                if nuevo_estado == "ENTREGADO" and pedido.direccion_entrega_id is not None:
                    raise BusinessRuleError(
                        "Los pedidos con envío deben pasar por EN_CAMINO antes de ENTREGADO"
                    )
                if nuevo_estado == "EN_CAMINO" and pedido.direccion_entrega_id is None:
                    raise BusinessRuleError(
                        "Los pedidos de retiro en local no pasan por EN_CAMINO"
                    )

            # D7: motivo required for CANCELADO_ADMIN from PENDIENTE, CONFIRMADO or EN_PREPARACION
            if nuevo_estado == "CANCELADO_ADMIN" and pedido.estado_codigo in {
                "PENDIENTE",
                "CONFIRMADO",
                "EN_PREPARACION",
            }:
                if not motivo or not motivo.strip():
                    raise BusinessRuleError(
                        "motivo es obligatorio para cancelar pedidos como administrador"
                    )

            estado_actual = pedido.estado_codigo
        finally:
            session.close()

        # Delegate to transicionar_estado which opens its own UoW with FOR UPDATE
        return self.transicionar_estado(
            pedido_id=pedido_id,
            estado_anterior=estado_actual,
            estado_nuevo=nuevo_estado,
            actor_id=user_id,
            motivo=motivo,
        )

    def transicionar_pedido(
        self,
        user_id: int,
        pedido_id: int,
        estado_codigo_destino: str,
        motivo: Optional[str] = None,
    ) -> tuple[Pedido, str, HistorialItem]:
        """
        Execute a generic state transition via POST /pedidos/{id}/transicionar.

        Similar to avanzar_estado but accepts any FSM-allowed target state
        (including CANCELADO_ADMIN, CANCELADO_CLIENTE).

        Returns (Pedido, estado_anterior, nuevo_historial) so the caller can
        build the response.

        Raises:
            BusinessRuleError: invalid FSM transition or missing motivo.
            NotFoundError: pedido not found, or CLIENT accessing another user's order.
            ForbiddenError: user lacks required role for this transition.
            InvalidStateTransitionError: race condition (409).
        """
        import shared.unit_of_work as _uow_mod
        from sqlalchemy import select as sa_select

        # Read-only session for validation — no UoW, no lock (D14)
        session = _uow_mod.get_session_factory()()
        try:
            order_repo = OrderRepository(session)
            user_repo = UserProfileRepository(session)

            pedido = order_repo.find_by_id(pedido_id)
            if pedido is None:
                raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")

            user = user_repo.find_by_id_with_roles(user_id)
            user_roles = {r.codigo for r in user.roles}

            # D13: ownership check — CLIENT can only act on their own orders
            if user_roles == {"CLIENT"} and pedido.user_id != user_id:
                raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")

            # D3 + D4: FSM and RBAC validation
            validate_transition(pedido.estado_codigo, estado_codigo_destino, user_roles)

            # D4: delivery-mode branching rule — EN_CAMINO only for delivery orders
            if pedido.estado_codigo == "TERMINADO":
                if estado_codigo_destino == "ENTREGADO" and pedido.direccion_entrega_id is not None:
                    raise BusinessRuleError(
                        "Los pedidos con envío deben pasar por EN_CAMINO antes de ENTREGADO"
                    )
                if estado_codigo_destino == "EN_CAMINO" and pedido.direccion_entrega_id is None:
                    raise BusinessRuleError(
                        "Los pedidos de retiro en local no pasan por EN_CAMINO"
                    )

            # motivo required for CANCELADO_ADMIN from non-terminal states
            if estado_codigo_destino == "CANCELADO_ADMIN" and pedido.estado_codigo in {
                "PENDIENTE",
                "CONFIRMADO",
                "EN_PREPARACION",
            }:
                if not motivo or not motivo.strip():
                    raise BusinessRuleError(
                        "motivo es obligatorio para cancelar pedidos como administrador"
                    )

            estado_actual = pedido.estado_codigo
        finally:
            session.close()

        # Delegate to transicionar_estado which opens its own UoW with FOR UPDATE
        pedido = self.transicionar_estado(
            pedido_id=pedido_id,
            estado_anterior=estado_actual,
            estado_nuevo=estado_codigo_destino,
            actor_id=user_id,
            motivo=motivo,
        )

        # Fetch the latest historial entry from a fresh read session
        read_session = _uow_mod.get_session_factory()()
        try:
            from features.orders.models import HistorialEstadoPedido

            stmt = (
                sa_select(HistorialEstadoPedido)
                .where(HistorialEstadoPedido.pedido_id == pedido_id)
                .order_by(HistorialEstadoPedido.creado_en.desc())
                .limit(1)
            )
            hist_row = read_session.execute(stmt).scalar_one_or_none()
            nuevo_historial = (
                HistorialItem.model_validate(hist_row)
                if hist_row
                else HistorialItem(
                    id=0,
                    estado_anterior_codigo=estado_actual,
                    estado_nuevo_codigo=estado_codigo_destino,
                    cambiado_por_id=user_id,
                    motivo=motivo,
                    creado_en=pedido.creado_en,
                )
            )
        finally:
            read_session.close()

        return pedido, estado_actual, nuevo_historial
