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

from backend.features.addresses.repository import AddressRepository
from backend.features.orders.models import Pedido
from backend.features.orders.repository import OrderRepository
from backend.features.orders.schemas import CrearPedidoRequest
from backend.shared.exceptions import BusinessRuleError, NotFoundError
from backend.shared.unit_of_work import UnitOfWork

# D5 — v1 fixed shipping cost. Replace with dynamic calculation in a future change.
SHIPPING_COST_DEFAULT = Decimal("50.00")


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
          9. Refresh created_at. UoW __exit__ commits.

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
                    raise NotFoundError(f"Producto no encontrado: id={item.producto_id}")
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
            costo_envio = SHIPPING_COST_DEFAULT if direccion is not None else Decimal("0.00")
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

            # ── Step 9: Refresh created_at before UoW closes session ──────
            uow.session.refresh(pedido, attribute_names=["created_at"])

            # UoW __exit__ commits on clean exit, rolls back on exception.
            return pedido
