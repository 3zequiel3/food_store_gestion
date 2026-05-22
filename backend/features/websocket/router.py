"""
WebSocket router — WS /ws endpoint + GET /ws/health.

Design:
  D3 — single register_realtime touchpoint exposes this router.
  D4 — topic/room scope derived from JWT at handshake; client-declared scope validated.
  D5 — inbound message router dispatches by "type"; unknown frames → error frame,
       never crash the connection.

Endpoint: WS /ws?token=<JWT>
  Auth: JWT validated at handshake; missing/invalid → close 1008.
  Scope: derived from JWT roles (see scope.py). Connection auto-subscribed to
  the default topic for its role; can additionally subscribe via inbound "subscribe".

Endpoint: GET /ws/health
  Returns drain task liveness + connection count. 200 always (degraded info in body).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from features.websocket.contracts import DomainEvent
from features.websocket.manager import connection_manager
from features.websocket.scope import default_topic, is_topic_allowed, scope_from_jwt
from shared.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Set by register_realtime — references to the module-level singleton state.
_drain_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


@router.get("/health", summary="WebSocket transport health")
async def ws_health() -> dict[str, Any]:
    """
    GET /ws/health

    Returns the transport status so the frontend can detect degraded mode
    and fall back to 30-second polling.

    Response:
      status         — "ok" if drain task is alive, "degraded" otherwise
      drain_alive    — bool
      connection_count — int, total active WS connections
    """
    global _drain_task
    drain_alive = _drain_task is not None and not _drain_task.done()
    count = connection_manager.connection_count()

    return {
        "status": "ok" if drain_alive else "degraded",
        "drain_alive": drain_alive,
        "connection_count": count,
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """
    WS /ws?token=<JWT>

    Handshake:
      1. Validate token (missing/invalid → close 1008).
      2. Derive scope from JWT roles.
      3. Accept and auto-subscribe to the default topic for the role.
      4. Enter the inbound message loop (dispatch by type).
      5. On disconnect, clean up all subscriptions.
    """
    # ── 1. Token validation ──────────────────────────────────────────────
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

    user_id: int = int(payload.get("sub", 0))
    roles: list[str] = payload.get("roles", [])

    # ── 2. Scope derivation ──────────────────────────────────────────────
    scope = scope_from_jwt(user_id=user_id, roles=roles)

    # ── 3. Accept + auto-subscribe ───────────────────────────────────────
    await websocket.accept()

    auto_topic = default_topic(scope)
    if auto_topic:
        await connection_manager.connect(websocket, topic=auto_topic)
        logger.debug("WS accepted user_id=%d roles=%s auto_topic=%s", user_id, roles, auto_topic)
    else:
        logger.debug("WS accepted user_id=%d roles=%s (no auto-topic)", user_id, roles)

    # ── 4. Inbound message loop ──────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_inbound(websocket, raw, scope, user_id, roles)
    except WebSocketDisconnect:
        logger.debug("WS disconnected user_id=%d", user_id)
    except Exception:
        logger.debug("WS connection lost user_id=%d", user_id, exc_info=True)
    finally:
        await connection_manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Inbound message router (D5 — Phase 1 subset; Phase 5 extends this)
# ---------------------------------------------------------------------------

_ERROR_FRAME = json.dumps({"v": 1, "type": "error", "payload": {"message": "unknown_type"}})


async def _handle_inbound(
    websocket: WebSocket,
    raw: str,
    scope: dict,
    user_id: int,
    roles: list[str],
) -> None:
    """
    Parse and dispatch an inbound text frame.

    Unknown or malformed frames → error frame sent back; connection stays open.
    """
    try:
        msg = json.loads(raw)
    except (ValueError, TypeError):
        await _send_error(websocket, "invalid_json")
        return

    msg_type = msg.get("type")

    if msg_type == "subscribe":
        await _handle_subscribe(websocket, msg, scope, user_id, roles)
    elif msg_type == "kitchen.ingredient_unavailable":
        await _handle_kitchen_ingredient_unavailable(websocket, msg, scope, roles)
    else:
        await _send_error(websocket, f"unknown_type:{msg_type}")


async def _handle_subscribe(
    websocket: WebSocket,
    msg: dict,
    scope: dict,
    user_id: int,
    roles: list[str],
) -> None:
    """Handle a client subscribe request. Validates topic against JWT scope."""
    topic = msg.get("topic", "")
    if not topic or not isinstance(topic, str):
        await _send_error(websocket, "subscribe_missing_topic")
        return

    if not is_topic_allowed(topic, scope, user_id=user_id, roles=roles):
        await _send_error(websocket, f"subscribe_denied:{topic}")
        return

    await connection_manager.connect(websocket, topic=topic)
    ack = json.dumps({"v": 1, "type": "subscribed", "payload": {"topic": topic}})
    try:
        await websocket.send_text(ack)
    except Exception:
        pass


async def _handle_kitchen_ingredient_unavailable(
    websocket: WebSocket,
    msg: dict,
    scope: dict,
    roles: list[str],
) -> None:
    """
    Handle kitchen.ingredient_unavailable inbound message.

    Authorization: COCINA or ADMIN only.
    Phase 1: stub — the actual service call is wired in Phase 5.
    """
    role_set = set(roles)
    if not role_set & {"COCINA", "ADMIN"}:
        await _send_error(websocket, "unauthorized:kitchen.ingredient_unavailable")
        return

    payload = msg.get("payload", {})
    order_id = payload.get("order_id")
    ingredient_id = payload.get("ingredient_id")

    if not order_id or not ingredient_id:
        await _send_error(websocket, "invalid_payload:kitchen.ingredient_unavailable")
        return

    # Phase 5 will wire this to the ingredient-availability service.
    logger.debug(
        "kitchen.ingredient_unavailable: order_id=%s ingredient_id=%s (Phase 5 stub)",
        order_id,
        ingredient_id,
    )


async def _send_error(websocket: WebSocket, reason: str) -> None:
    """Send an error frame to the client. Never raises."""
    try:
        frame = json.dumps({"v": 1, "type": "error", "payload": {"reason": reason}})
        await websocket.send_text(frame)
    except Exception:
        pass
