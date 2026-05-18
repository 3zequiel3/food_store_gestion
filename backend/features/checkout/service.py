"""Checkout service — atomic pay-first order creation.

This module provides the business logic for creating orders with integrated
payment processing. The order is only persisted if:
- Online payment: MP returns approved status
- Pickup+efectivo: No payment required, order created directly

Decisions implemented:
- D1: Pedido se crea POST-checkout, no PRE-checkout
- D3: Modo estricto MP — solo approved crea pedido
- D5: Pedido + Pago en una sola transacción UoW
- D6: external_reference = idempotency_key (UUID4)
- D11: Validación server-side total, recálculo de totales
- D12: Idempotencia con idempotency_key del front
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import mercadopago
from mercadopago.config import RequestOptions

from config import settings
from features.checkout.exceptions import (
    PaymentCancelledError,
    PaymentPendingNotAcceptedError,
    PaymentRejectedError,
    PaymentUnexpectedStatusError,
)
from features.checkout.schemas import (
    CheckoutOnlineRequest,
    CheckoutOnlineResponse,
    CheckoutPickupEfectivoRequest,
    CheckoutPickupEfectivoResponse,
)
from features.orders.models import DetallePedido, HistorialEstadoPedido, Pedido
from features.orders.repository import OrderRepository
from features.payments.models import Pago
from features.payments.repository import PaymentRepository
from features.products.repository import ProductRepository
from shared.exceptions import BusinessRuleError, NotFoundError, UpstreamError
from shared.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

COSTO_ENVIO = Decimal("50.00")


class CheckoutService:
    """Service for checkout operations with atomic order+payment creation."""

    def __init__(self) -> None:
        pass

    def _get_sdk(self) -> mercadopago.SDK:
        """Get configured MercadoPago SDK instance."""
        return mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    def _validar_y_calcular_carrito(
        self,
        session: Session,
        user_id: int,
        items: list,
        direccion_id: int | None,
        tipo_entrega: str | None,
    ) -> tuple[list[tuple], Decimal]:
        """
        Validate cart items and calculate total.
        
        Args:
            session: DB session for queries
            user_id: Current user ID
            items: List of CheckoutItem
            direccion_id: Optional delivery address ID
            tipo_entrega: Optional delivery type (DELIVERY/PICKUP)
        
        Returns:
            Tuple of (validated_items, total_amount)
            where validated_items is list of (producto, cantidad, precio_unitario)
        
        Raises:
            NotFoundError: Product not found or belongs to another user
            BusinessRuleError: Stock insufficient or product not available
        """
        product_repo = ProductRepository(session)
        validated_items = []
        subtotal = Decimal("0.00")

        for item in items:
            # Validate product exists and is available
            producto = product_repo.find_by_id(item.producto_id)
            if producto is None:
                raise NotFoundError(f"Producto no encontrado: id={item.producto_id}")
            
            if not producto.disponible:
                raise BusinessRuleError(
                    f"El producto '{producto.nombre}' no está disponible",
                    code="product_not_available"
                )

            # Validate stock
            if producto.stock is not None and producto.stock >= 0:
                if item.cantidad > producto.stock:
                    raise BusinessRuleError(
                        f"Stock insuficiente para '{producto.nombre}': "
                        f"disponible {producto.stock}, solicitado {item.cantidad}",
                        code="insufficient_stock"
                    )

            # Calculate item total
            precio_unitario = Decimal(str(producto.precio))
            item_total = precio_unitario * item.cantidad
            subtotal += item_total

            validated_items.append((
                producto,
                item.cantidad,
                precio_unitario,
                item.personalizacion or []
            ))

        # Calculate shipping cost
        costo_envio = COSTO_ENVIO if (tipo_entrega == "DELIVERY" and direccion_id is not None) else Decimal("0.00")
        total = subtotal + costo_envio

        return validated_items, total

    def _check_existing_payment(
        self,
        session: Session,
        idempotency_key: UUID,
    ) -> Pago | None:
        """Check if a payment already exists for this idempotency_key.
        
        Returns the existing Pago if found, None otherwise.
        """
        payment_repo = PaymentRepository(session)
        return payment_repo.find_by_external_reference(str(idempotency_key))

    def crear_pedido_online(
        self,
        user_id: int,
        request: CheckoutOnlineRequest,
    ) -> CheckoutOnlineResponse:
        """
        Create an order with online payment via MercadoPago.
        
        The order is only created if MP returns approved status.
        All operations (order + payment) happen in a single transaction.
        
        Args:
            user_id: Authenticated user ID
            request: CheckoutOnlineRequest with payment details
        
        Returns:
            CheckoutOnlineResponse with order and payment IDs
        
        Raises:
            PaymentRejectedError: MP rejected the payment
            PaymentPendingNotAcceptedError: MP returned pending/in_process (strict mode)
            PaymentCancelledError: MP returned cancelled status
            PaymentUnexpectedStatusError: MP returned unknown status
            UpstreamError: MP unreachable or error
            BusinessRuleError: Stock insufficient, product unavailable, etc.
            NotFoundError: Product or address not found
        """
        # Phase 1: Validate cart and calculate total (read-only)
        # Also check idempotency
        with UnitOfWork() as uow:
            validated_items, total = self._validar_y_calcular_carrito(
                uow.session,
                user_id,
                request.items,
                request.direccion_id,
                request.tipo_entrega,
            )

            # Check if this is a retry with same idempotency_key
            existing_pago = self._check_existing_payment(
                uow.session,
                request.idempotency_key,
            )
            if existing_pago is not None:
                # Return cached result without re-calling MP. The Pago model
                # does not persist status_detail (only mp_status, mp_payment_id
                # and external_reference are stored), so we return an empty
                # string for status_detail on retries.
                logger.info(
                    "Returning cached checkout result for idempotency_key=%s",
                    request.idempotency_key
                )
                return CheckoutOnlineResponse(
                    pedido_id=existing_pago.pedido_id,
                    pago_id=existing_pago.id,
                    mp_status=existing_pago.mp_status or "approved",
                    mp_id=str(existing_pago.mp_payment_id) if existing_pago.mp_payment_id else "",
                    status_detail="",
                )

        # Phase 2: Call MercadoPago (outside UoW as it's external)
        sdk = self._get_sdk()
        request_options = RequestOptions(
            custom_headers={"X-Idempotency-Key": str(request.idempotency_key)}
        )

        payment_data = {
            "transaction_amount": float(total),
            "token": request.card_token,
            "description": f"Pedido de Food Store",
            "installments": request.installments,
            "payment_method_id": request.payment_method_id,
            "payer": {
                "identification": {
                    "type": request.identification_type,
                    "number": request.identification_number,
                }
            },
            "external_reference": str(request.idempotency_key),
        }

        try:
            mp_response = sdk.payment().create(payment_data, request_options)
            mp_result = mp_response["response"]
        except Exception as e:
            logger.exception("MercadoPago unreachable: %s", e)
            raise UpstreamError(
                "MercadoPago no respondió. Intentá de nuevo en un momento.",
                code="mp_unreachable",
            )

        # Check if MP returned a status
        mp_status = mp_result.get("status")
        status_detail = mp_result.get("status_detail", "")
        mp_payment_id = mp_result.get("id")

        if mp_status is None:
            # MP responded but without status (error case)
            error_msg = mp_result.get("message", "Error desconocido")
            logger.error("MP error without status: %s", mp_result)
            raise UpstreamError(
                f"MercadoPago no devolvió estado: {error_msg}",
                code="mp_unreachable",
            )

        # Phase 3: Handle MP status (strict mode - only approved creates order)
        if mp_status == "approved":
            # Happy path: create order + payment atomically
            return self._crear_pedido_y_pago_aprobado(
                user_id=user_id,
                request=request,
                validated_items=validated_items,
                total=total,
                mp_payment_id=mp_payment_id,
                status_detail=status_detail,
            )
        elif mp_status == "rejected":
            raise PaymentRejectedError(mp_status, status_detail)
        elif mp_status in ("pending", "in_process"):
            raise PaymentPendingNotAcceptedError(mp_status, status_detail)
        elif mp_status == "cancelled":
            raise PaymentCancelledError(mp_status, status_detail)
        else:
            # Unknown status
            raise PaymentUnexpectedStatusError(mp_status, status_detail)

    def _crear_pedido_y_pago_aprobado(
        self,
        user_id: int,
        request: CheckoutOnlineRequest,
        validated_items: list,
        total: Decimal,
        mp_payment_id: str | int,
        status_detail: str,
    ) -> CheckoutOnlineResponse:
        """
        Create order and payment atomically after MP approved.
        
        This is an internal method - do not call directly.
        All DB operations happen in a single UoW.
        """
        try:
            with UnitOfWork() as uow:
                # Create Pedido. forma_pago_codigo is the FK to payment_methods
                # — for online MP checkout it is always 'TARJETA' (renamed from
                # MERCADOPAGO in migration 20260514_1200). The request's
                # payment_method_id is the MP-specific card brand identifier
                # ('visa', 'master', etc.) and is NOT a valid catalog code.
                pedido = Pedido(
                    user_id=user_id,
                    estado_codigo="PENDIENTE",
                    forma_pago_codigo="TARJETA",
                    total=total,
                    direccion_entrega_id=request.direccion_id,
                    costo_envio=COSTO_ENVIO if request.direccion_id else Decimal("0.00"),
                    notas=request.notas,
                )
                uow.session.add(pedido)
                uow.session.flush()  # Get pedido.id

                # Create DetallePedido items. The model only persists
                # nombre/precio snapshots and cantidad — there is no
                # precio_unitario column.
                for producto, cantidad, precio_unitario, personalizacion in validated_items:
                    detalle = DetallePedido(
                        pedido_id=pedido.id,
                        producto_id=producto.id,
                        cantidad=cantidad,
                        precio_snapshot=precio_unitario,
                        nombre_snapshot=producto.nombre,
                        personalizacion=personalizacion or None,
                    )
                    uow.session.add(detalle)

                # Create HistorialEstadoPedido
                historial = HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_anterior_codigo=None,
                    estado_nuevo_codigo="PENDIENTE",
                    cambiado_por_id=user_id,
                    motivo=None,
                )
                uow.session.add(historial)

                # Create Pago. Required NOT NULL fields per the model:
                # pedido_id, monto, forma_pago_codigo, idempotency_key.
                # status_detail is NOT a column on the Pago model — it lives
                # only in the API response, not in the DB.
                pago = Pago(
                    pedido_id=pedido.id,
                    monto=total,
                    forma_pago_codigo="TARJETA",
                    idempotency_key=str(request.idempotency_key),
                    mp_status="approved",
                    mp_payment_id=str(mp_payment_id),
                    external_reference=str(request.idempotency_key),
                )
                uow.session.add(pago)
                uow.session.flush()  # Get pago.id

                # Commit happens on successful exit from context manager
                logger.info(
                    "Created order %d with payment %d (MP id: %s) for user %d",
                    pedido.id,
                    pago.id,
                    mp_payment_id,
                    user_id
                )

                return CheckoutOnlineResponse(
                    pedido_id=pedido.id,
                    pago_id=pago.id,
                    mp_status="approved",
                    mp_id=str(mp_payment_id),
                    status_detail=status_detail,
                )

        except Exception as e:
            # Log the incident - MP already charged but we failed to persist
            logger.exception(
                "CRITICAL: MP approved payment but persistence failed. "
                "mp_payment_id=%s, idempotency_key=%s, user_id=%d, error=%s",
                mp_payment_id,
                request.idempotency_key,
                user_id,
                e,
            )
            # Re-raise as upstream error to indicate system failure.
            # Uses shared.exceptions.UpstreamError which has a registered
            # 502 handler in main.py.
            raise UpstreamError(
                "El pago fue procesado pero hubo un error al guardar el pedido. "
                "Contactá a soporte con tu comprobante de pago.",
                code="persistence_failed",
            )

    def crear_pedido_pickup_efectivo(
        self,
        user_id: int,
        request: CheckoutPickupEfectivoRequest,
    ) -> CheckoutPickupEfectivoResponse:
        """
        Create a pickup order with cash payment (no online payment).
        
        Args:
            user_id: Authenticated user ID
            request: CheckoutPickupEfectivoRequest
        
        Returns:
            CheckoutPickupEfectivoResponse with order ID
        
        Raises:
            BusinessRuleError: Stock insufficient, product unavailable
            NotFoundError: Product not found
        """
        with UnitOfWork() as uow:
            # Validate cart and calculate total
            validated_items, total = self._validar_y_calcular_carrito(
                uow.session,
                user_id,
                request.items,
                direccion_id=None,
                tipo_entrega="PICKUP",
            )

            # Create Pedido
            pedido = Pedido(
                user_id=user_id,
                estado_codigo="PENDIENTE",
                forma_pago_codigo="EFECTIVO",
                total=total,
                direccion_entrega_id=None,
                direccion_snapshot=None,
                costo_envio=Decimal("0.00"),
                notas=request.notas,
            )
            uow.session.add(pedido)
            uow.session.flush()  # Get pedido.id

            # Create DetallePedido items. The model only persists snapshots
            # + cantidad — there is no precio_unitario column.
            for producto, cantidad, precio_unitario, personalizacion in validated_items:
                detalle = DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=producto.id,
                    cantidad=cantidad,
                    precio_snapshot=precio_unitario,
                    nombre_snapshot=producto.nombre,
                    personalizacion=personalizacion or None,
                )
                uow.session.add(detalle)

            # Create HistorialEstadoPedido
            historial = HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_anterior_codigo=None,
                estado_nuevo_codigo="PENDIENTE",
                cambiado_por_id=user_id,
                motivo=None,
            )
            uow.session.add(historial)

            # No Pago created for efectivo

            logger.info(
                "Created pickup+efectivo order %d for user %d",
                pedido.id,
                user_id
            )

            return CheckoutPickupEfectivoResponse(
                pedido_id=pedido.id,
            )
