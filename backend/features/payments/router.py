"""
Payments feature router.

Endpoints for payment management and webhooks.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{payment_id}")
async def get_payment(payment_id: str):
    """
    Get payment by ID.

    Implementation in payments feature.
    """
    return {"status": "not_implemented"}


@router.post("/")
async def create_payment():
    """
    Create new payment.

    Implementation in payments feature.
    """
    return {"status": "not_implemented"}


@router.post("/webhook/mercadopago")
async def webhook_mercadopago():
    """
    MercadoPago webhook handler.

    Implementation in payments feature.
    """
    return {"status": "not_implemented"}
