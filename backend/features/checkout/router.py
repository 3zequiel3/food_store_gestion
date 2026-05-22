"""
Checkout router — registered in main.py under /api/v1/checkout.

Endpoints:
  POST /api/v1/checkout/online         — Create order with online payment (MP)
  POST /api/v1/checkout/pickup-efectivo — Create pickup order with cash payment

Auth: Both endpoints require CLIENT role.
Idempotency: online endpoint uses idempotency_key for MP and local deduplication.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from features.auth.dependencies import require_role
from features.checkout.exceptions import (
    PaymentCancelledError,
    PaymentPendingNotAcceptedError,
    PaymentRejectedError,
    PaymentUnexpectedStatusError,
)
from features.checkout.schemas import (
    CheckoutDeliveryEfectivoRequest,
    CheckoutDeliveryEfectivoResponse,
    CheckoutErrorResponse,
    CheckoutOnlineRequest,
    CheckoutOnlineResponse,
    CheckoutPickupEfectivoRequest,
    CheckoutPickupEfectivoResponse,
)
from features.checkout.service import CheckoutService
from features.users.models import Usuario
from shared.exceptions import BusinessRuleError, NotFoundError, UpstreamError

router = APIRouter()


def _handle_checkout_error(error: Exception) -> HTTPException:
    """Map checkout exceptions to HTTP responses."""
    if isinstance(error, PaymentRejectedError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": error.code,
                "detail": str(error),
                "mp_status": error.mp_status,
                "status_detail": error.status_detail,
            },
        )
    elif isinstance(error, PaymentPendingNotAcceptedError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": error.code,
                "detail": str(error),
                "mp_status": error.mp_status,
                "status_detail": error.status_detail,
            },
        )
    elif isinstance(error, PaymentCancelledError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": error.code,
                "detail": str(error),
                "mp_status": error.mp_status,
                "status_detail": error.status_detail,
            },
        )
    elif isinstance(error, PaymentUnexpectedStatusError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": error.code,
                "detail": str(error),
                "mp_status": error.mp_status,
                "status_detail": error.status_detail,
            },
        )
    elif isinstance(error, UpstreamError):
        if error.code in {"mp_unreachable", "mp_bad_request"}:
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": error.code,
                    "detail": str(error),
                },
            )
        else:
            # persistence_failed or other critical errors
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": error.code,
                    "detail": str(error),
                },
            )
    elif isinstance(error, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "not_found",
                "detail": str(error),
            },
        )
    elif isinstance(error, BusinessRuleError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": error.code,
                "detail": str(error),
            },
        )
    else:
        # Unexpected error
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_error",
                "detail": "Error interno del servidor",
            },
        )


@router.post(
    "/online",
    response_model=CheckoutOnlineResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        402: {"model": CheckoutErrorResponse, "description": "Payment required/rejected"},
        422: {"model": CheckoutErrorResponse, "description": "Validation error"},
        502: {"model": CheckoutErrorResponse, "description": "Upstream service error"},
        500: {"model": CheckoutErrorResponse, "description": "Internal server error"},
    },
)
def checkout_online(
    body: CheckoutOnlineRequest,
    current_user: Usuario = Depends(require_role("CLIENT")),
) -> CheckoutOnlineResponse:
    """
    Create an order with online payment via MercadoPago.

    The order is only created if MP returns approved status (strict mode D3).
    Any other status (rejected, pending, in_process, cancelled) returns 402
    without creating an order.

    Idempotency: The same idempotency_key within a short window returns
    the cached result without re-charging the card.
    """
    try:
        service = CheckoutService()
        return service.crear_pedido_online(
            user_id=current_user.id,
            request=body,
            user_email=current_user.email,
        )
    except Exception as e:
        http_error = _handle_checkout_error(e)
        raise http_error


@router.post(
    "/pickup-efectivo",
    response_model=CheckoutPickupEfectivoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": CheckoutErrorResponse, "description": "Validation error"},
    },
)
def checkout_pickup_efectivo(
    body: CheckoutPickupEfectivoRequest,
    current_user: Usuario = Depends(require_role("CLIENT")),
) -> CheckoutPickupEfectivoResponse:
    """
    Create a pickup order with cash payment (no online payment).

    The order is created directly in PENDIENTE state. Payment happens
    at the counter when the customer picks up the order.
    """
    try:
        service = CheckoutService()
        return service.crear_pedido_pickup_efectivo(
            user_id=current_user.id,
            request=body,
        )
    except Exception as e:
        http_error = _handle_checkout_error(e)
        raise http_error


@router.post(
    "/delivery-efectivo",
    response_model=CheckoutDeliveryEfectivoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": CheckoutErrorResponse, "description": "Address not found"},
        422: {"model": CheckoutErrorResponse, "description": "Validation error"},
    },
    summary="Cash-on-delivery order",
    description=(
        "Create a delivery order with cash payment (P0.2). "
        "The order is created in PENDIENTE state with shipping cost included. "
        "Payment is collected at the door — no Pago record is created. "
        "Requires CLIENT role."
    ),
)
def checkout_delivery_efectivo(
    body: CheckoutDeliveryEfectivoRequest,
    current_user: Usuario = Depends(require_role("CLIENT")),
) -> CheckoutDeliveryEfectivoResponse:
    """
    POST /api/v1/checkout/delivery-efectivo — cash-on-delivery.

    The customer receives the order at their address and pays the driver in cash.
    Mirrors the pickup-efectivo endpoint but adds shipping cost and stores
    the delivery address on the Pedido.

    Authentication: cookie-backed session (CLIENT role).
    HTTP mapping:
      NotFoundError → 404 (product or address not found)
      BusinessRuleError → 422 (stock, availability, invalid personalizacion)
    """
    try:
        service = CheckoutService()
        return service.crear_pedido_delivery_efectivo(
            user_id=current_user.id,
            request=body,
        )
    except Exception as e:
        http_error = _handle_checkout_error(e)
        raise http_error
