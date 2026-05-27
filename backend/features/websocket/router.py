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

from features.websocket.manager import connection_manager
from features.websocket.scope import default_topic, is_topic_allowed, scope_from_jwt
from shared.security import decode_access_token

# Availability service import — used by the report wiring (task 6.17).
# Imported here (not lazily) so tests can patch _report_service_call directly.
from features.availability.service import IngredientAvailabilityService as _IngredientSvc

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
        await _handle_kitchen_ingredient_unavailable(websocket, msg, roles, user_id=user_id)
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
    
    if topic.startswith("order:") and not scope.get("orders_all"):
        if not _client_owns_order(topic, user_id):
            await _send_error(websocket, f"subscribe_denied:{topic}")
            return

    await connection_manager.connect(websocket, topic=topic)
    ack = json.dumps({"v": 1, "type": "subscribed", "payload": {"topic": topic}})
    try:
        await websocket.send_text(ack)
    except Exception:
        pass


def kitchen_ingredient_unavailable_stub(*, order_id: int, ingredient_id: int) -> None:
    """
    Phase-6 stub — retained for backward compatibility with Phase-5 tests.

    As of Phase 6 task 6.17 this stub is NO LONGER called by the handler;
    the handler now routes to _report_service_call instead. The stub remains
    importable so existing test assertions against it still pass without changes.
    """
    logger.debug(
        "kitchen.ingredient_unavailable_stub: order_id=%s ingredient_id=%s "
        "(Phase-6 stub — no longer in the active handler path)",
        order_id,
        ingredient_id,
    )


def _report_service_call(*, user_id: int, order_id: int, ingredient_id: int) -> None:
    """
    Task 6.17 — wires the inbound kitchen.ingredient_unavailable message to the
    IngredientAvailabilityService.report_unavailable() in a single UoW.

    This is a sync function because the service layer uses sync SQLAlchemy sessions.
    The WS handler awaits _handle_kitchen_ingredient_unavailable which calls this
    synchronously — consistent with the existing order-service pattern.

    Best-effort: any exception is swallowed to avoid crashing the WebSocket connection.
    """
    try:
        from shared.unit_of_work import UnitOfWork
        from features.websocket.registration import get_event_publisher

        publisher = get_event_publisher()

        with UnitOfWork() as uow:
            svc = _IngredientSvc(session=uow.session, publisher=publisher)
            svc.report_unavailable(
                ingrediente_id=ingredient_id,
                reportado_por=user_id,
                pedido_id=order_id,
            )
        # UoW commits on clean exit — publish happens inside service (post-flush, pre-commit).
        logger.debug(
            "_report_service_call: reported ingredient_id=%d unavailable "
            "(order_id=%d, user_id=%d)",
            ingredient_id,
            order_id,
            user_id,
        )
    except Exception:
        logger.debug(
            "_report_service_call: failed to report ingredient_id=%d (best-effort, swallowed)",
            ingredient_id,
            exc_info=True,
        )


def _client_owns_order(topic: str, user_id: int) -> bool | None:
    """
    Verify that the pedido in the topic 'order:{N}' belongs to user_id.

    Used by the WS subscribe handler to enforce ownership on CLIENT
    subscriptions to `order:{N}` topics (D4 hardening). Staff with the
    `orders_all` scope skip this check at the call site.

    Returns False on parse errors, missing pedido, ownership mismatch, or any
    DB exception (fail closed).
    """
    try:
        order_id = int(topic.split(":", 1)[1])
    except (IndexError, ValueError):
        return False

    try:
        from shared.unit_of_work import UnitOfWork
        from features.orders.repository import OrderRepository

        with UnitOfWork() as uow:
            repo = OrderRepository(session=uow.session)
            return repo.pedido_belongs_to_user(pedido_id=order_id, user_id=user_id)
    except Exception:
        logger.debug(
            "_client_owns_order: ownership check failed for topic=%s user=%d "
            "(failing closed)",
            topic,
            user_id,
            exc_info=True,
        )
        return False


async def _handle_kitchen_ingredient_unavailable(
    websocket: WebSocket,
    msg: dict,
    roles: list[str],
    user_id: int = 0,
) -> None:
    """
    Handle kitchen.ingredient_unavailable inbound message.

    Authorization: COCINA or ADMIN only (re-checked from JWT roles, D5).
    Payload: {order_id: int, ingredient_id: int} — both required.
    On success: calls _report_service_call → IngredientAvailabilityService (task 6.17).
    On auth failure: error frame sent, no side-effects.
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

    # Task 6.17: replaced the Phase-5 stub with the real service call.
    _report_service_call(user_id=user_id, order_id=order_id, ingredient_id=ingredient_id)


async def _send_error(websocket: WebSocket, reason: str) -> None:
    """Send an error frame to the client. Never raises."""
    try:
        frame = json.dumps({"v": 1, "type": "error", "payload": {"reason": reason}})
        await websocket.send_text(frame)
    except Exception:
        pass
