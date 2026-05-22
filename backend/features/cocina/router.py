"""
Kitchen Display System (KDS) router.

GET /api/v1/cocina/pedidos — REST endpoint for initial load + polling fallback.

Phase 1 cutover: the WS /api/v1/cocina/ws endpoint has been removed.
Real-time updates for the KDS are now served through the shared transport:
  WS /ws?token=<JWT>  (features/websocket/router.py)
A COCINA connection auto-subscribes to kitchen:all at handshake.

Authorization: COCINA and ADMIN roles only. CLIENT gets 403.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from features.auth.dependencies import require_role
from features.cocina.schemas import CocinaPedidoResponse
from features.cocina.service import get_kitchen_orders
from features.users.models import Usuario

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# REST endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/pedidos",
    response_model=list[CocinaPedidoResponse],
    status_code=200,
    summary="Pedidos en cocina",
    description=(
        "Devuelve los pedidos en estado CONFIRMADO y EN_PREPARACION, "
        "ordenados por antigüedad de entrada a cocina (RN-CO02). "
        "Requiere rol COCINA o ADMIN."
    ),
)
async def get_pedidos_cocina(
    _user: Usuario = Depends(require_role("COCINA", "ADMIN")),
) -> list[CocinaPedidoResponse]:
    """
    GET /api/v1/cocina/pedidos

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: require_role("COCINA", "ADMIN") — 403 otherwise.
    """
    return get_kitchen_orders()
