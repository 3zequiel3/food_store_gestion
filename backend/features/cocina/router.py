"""
Kitchen Display System (KDS) router.

D6: GET /api/v1/cocina/pedidos — REST endpoint for initial load + polling fallback.
D5: WS /api/v1/cocina/ws — WebSocket for real-time push.

Authorization: COCINA and ADMIN roles only (D3). CLIENT gets 403.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from features.auth.dependencies import get_current_user, require_role
from features.cocina.schemas import CocinaPedidoResponse
from features.cocina.service import get_kitchen_orders
from features.cocina.ws_manager import ws_manager
from features.users.models import Usuario
from shared.exceptions import ForbiddenError, UnauthorizedError
from shared.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# REST endpoint — D6
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


# ---------------------------------------------------------------------------
# WebSocket endpoint — D5
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def cocina_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """
    WS /api/v1/cocina/ws?token=<JWT>

    Real-time push for KDS screens. Auth validated in handshake:
    - Missing or invalid token → close 1008
    - Valid token but no COCINA/ADMIN role → close 1008
    - Valid token with COCINA/ADMIN → register connection, keep alive
    """
    # ── Validate token ──────────────────────────────────────────────────
    if not token:
        await websocket.close(code=1008, reason="Token requerido")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Token inválido o expirado")
        return

    if payload.get("type") != "access":
        await websocket.close(code=1008, reason="Tipo de token inválido")
        return

    roles = payload.get("roles", [])
    if not {"COCINA", "ADMIN"}.intersection(set(roles)):
        await websocket.close(code=1008, reason="Rol no autorizado")
        return

    # ── Accept and register ─────────────────────────────────────────────
    await websocket.accept()
    await ws_manager.connect(websocket)

    try:
        # Keep the connection alive. The client doesn't send messages;
        # we just wait for disconnect.
        while True:
            # receive_text blocks until the client disconnects or sends data.
            # KDS clients don't send messages, so this is essentially a
            # disconnect detector.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("KDS WebSocket client disconnected normally")
    except Exception:
        logger.info("KDS WebSocket connection lost")
    finally:
        await ws_manager.disconnect(websocket)
