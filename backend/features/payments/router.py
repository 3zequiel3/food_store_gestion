"""
Payments router — registered in main.py under /api/v1/pagos.

Endpoints:
  POST /api/v1/pagos/webhook/mercadopago  — IPN handler (no auth — MP calls this)
  GET  /api/v1/pagos/pedido/{pedido_id}   — latest payment status for an order

NOTE: POST / (crear pago) has been removed. Payment creation now happens
internally within POST /api/v1/checkout/online (checkout-pay-first-flow change).

Webhook format tolerance (three MP notification formats are normalised here):
  Format 1 — Modern webhook: POST JSON {"type": "payment", "data": {"id": "123"}}
  Format 2 — Old IPN body:   POST JSON {"topic": "payment", "resource": "https://.../payments/123"}
  Format 3 — Classic IPN:    POST (empty body) + query params ?topic=payment&id=123
"""

from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from features.auth.dependencies import require_role
from features.payments.schemas import PagoCreate, PagoCreateResponse, PagoRead
from features.payments.service import PaymentService
from features.users.models import Usuario

router = APIRouter()


def _extract_mp_payment_id(
    body: dict,
    topic: Optional[str],
    payment_id: Optional[str],
) -> Optional[str]:
    # Format 1 — modern webhook body
    if body.get("type") == "payment":
        pid = body.get("data", {}).get("id")
        if pid:
            return str(pid)
    # Format 2 — old IPN with resource URL
    if body.get("topic") == "payment":
        match = re.search(r"/payments/(\d+)", body.get("resource", ""))
        if match:
            return match.group(1)
    # Format 3 — classic IPN via query params
    if topic == "payment" and payment_id:
        return str(payment_id)
    return None


# NOTE: POST / (crear pago) has been removed.
# Payment creation now happens internally within POST /api/v1/checkout/online
# (checkout-pay-first-flow change).

@router.post("/webhook/mercadopago", status_code=200)
async def webhook_mercadopago(
    request: Request,
    topic: Optional[str] = Query(default=None),
    payment_id: Optional[str] = Query(default=None, alias="id"),
) -> dict:
    """
    Receive IPN notifications from MercadoPago.

    Tolerates all three notification formats MP may send.
    No user authentication — MP calls this endpoint directly.
    Idempotent: safe to receive the same notification multiple times.
    """
    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass

    mp_payment_id = _extract_mp_payment_id(body, topic, payment_id)
    if mp_payment_id:
        PaymentService().procesar_webhook(mp_payment_id)
    return {"status": "ok"}


@router.get("/pedido/{pedido_id}", response_model=PagoRead)
def obtener_pago_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(require_role("CLIENT")),
) -> PagoRead:
    """
    Return the latest payment status for an order owned by the authenticated client.
    """
    pago = PaymentService().obtener_pago_por_pedido(
        user_id=current_user.id,
        pedido_id=pedido_id,
    )
    return PagoRead.model_validate(pago)
