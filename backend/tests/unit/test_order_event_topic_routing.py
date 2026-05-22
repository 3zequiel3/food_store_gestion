"""
Unit tests — Task 4.7: order_state_changed topic routing.

The backend must fan out `order_state_changed` to:
  - `order:{id}`   → owning client subscriber
  - `orders:all`   → admin/PEDIDOS subscriber
  - `kitchen:all`  → COCINA/ADMIN subscriber (kitchen-relevant states only)

A client subscribed to `order:10` MUST NOT receive events published to `order:11`.

Design D2/D4: every publish call is best-effort; multiple events (one per topic)
are enqueued so each consumer class gets the right routing key.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Context manager — inject a MagicMock publisher so we can capture publish() calls
# ---------------------------------------------------------------------------


@contextmanager
def _mock_publisher():
    """
    Patch the _event_publisher singleton in features.websocket.registration so
    that get_event_publisher() returns a MagicMock capturing all publish() calls.
    """
    mock = MagicMock()
    with patch("features.websocket.registration._event_publisher", mock):
        yield mock


# ---------------------------------------------------------------------------
# Helper — extract DomainEvent args from mock.publish.call_args_list
# ---------------------------------------------------------------------------


def _published_events(mock_publisher) -> list:
    """Return list of DomainEvent objects passed to publisher.publish()."""
    return [call.args[0] for call in mock_publisher.publish.call_args_list]


# ---------------------------------------------------------------------------
# Task 4.7 — _publish_order_state_event fans out to the correct topics
# ---------------------------------------------------------------------------


class TestOrderStateEventTopicRouting:
    """
    _publish_order_state_event must emit multiple DomainEvents:
      - topic "order:{id}"  — for the owning client
      - topic "orders:all"  — for admin consumers (always, for every state change)
      - topic "kitchen:all" — only for kitchen-relevant states

    The function is injected with a mock publisher so we can inspect each
    published event without running an async event loop.
    """

    @pytest.mark.parametrize("kitchen_state", [
        "CONFIRMADO", "EN_PREPARACION", "TERMINADO",
        "CANCELADO", "CANCELADO_ADMIN", "CANCELADO_CLIENTE",
    ])
    def test_kitchen_state_fans_out_to_three_topics(self, kitchen_state: str):
        """
        For kitchen-relevant states the function emits events on three topics:
        order:{id}, orders:all, kitchen:all.
        """
        from features.orders import service as orders_service

        with _mock_publisher() as mock:
            orders_service._publish_order_state_event(pedido_id=42, estado_nuevo=kitchen_state)

        events = _published_events(mock)
        topics = {e.topic for e in events}

        assert "order:42" in topics, f"Missing order:42 in {topics}"
        assert "orders:all" in topics, f"Missing orders:all in {topics}"
        assert "kitchen:all" in topics, f"Missing kitchen:all in {topics}"

    @pytest.mark.parametrize("non_kitchen_state", ["PENDIENTE", "ENTREGADO"])
    def test_non_kitchen_state_fans_out_to_two_topics_no_kitchen(self, non_kitchen_state: str):
        """
        For states not in _KITCHEN_STATES the function emits two events:
        order:{id} and orders:all — but NOT kitchen:all.
        """
        from features.orders import service as orders_service

        with _mock_publisher() as mock:
            orders_service._publish_order_state_event(pedido_id=99, estado_nuevo=non_kitchen_state)

        events = _published_events(mock)
        topics = {e.topic for e in events}

        assert "order:99" in topics, f"Missing order:99 in {topics}"
        assert "orders:all" in topics, f"Missing orders:all in {topics}"
        assert "kitchen:all" not in topics, (
            f"kitchen:all must NOT be present for non-kitchen state {non_kitchen_state!r}"
        )

    def test_client_receives_only_own_order_event(self):
        """
        Each pedido_id produces its own 'order:{id}' topic — topics are isolated.
        A subscriber on order:10 must not receive events for order:11.
        """
        from features.orders import service as orders_service

        with _mock_publisher() as mock:
            orders_service._publish_order_state_event(pedido_id=10, estado_nuevo="CONFIRMADO")
            orders_service._publish_order_state_event(pedido_id=11, estado_nuevo="CONFIRMADO")

        events = _published_events(mock)
        order_topics = {e.topic for e in events if e.topic.startswith("order:")}

        assert "order:10" in order_topics
        assert "order:11" in order_topics

        # Payload correctness: events on order:10 carry order_id=10, not 11
        events_for_10 = [e for e in events if e.topic == "order:10"]
        for ev in events_for_10:
            assert ev.payload["order_id"] == 10, (
                f"Event on order:10 has wrong order_id in payload: {ev.payload}"
            )

        events_for_11 = [e for e in events if e.topic == "order:11"]
        for ev in events_for_11:
            assert ev.payload["order_id"] == 11, (
                f"Event on order:11 has wrong order_id in payload: {ev.payload}"
            )

    def test_all_emitted_events_have_versioned_contract(self):
        """
        Every emitted DomainEvent must have v=1, type=order_state_changed,
        a payload dict with order_id + estado, and a ts.
        """
        from features.orders import service as orders_service

        with _mock_publisher() as mock:
            orders_service._publish_order_state_event(pedido_id=5, estado_nuevo="EN_PREPARACION")

        events = _published_events(mock)
        assert events, "No events were published"

        for ev in events:
            assert ev.v == 1, f"Expected v=1, got {ev.v}"
            assert ev.type == "order_state_changed", f"Expected type=order_state_changed, got {ev.type!r}"
            assert isinstance(ev.payload, dict)
            assert "order_id" in ev.payload, f"Missing order_id in payload: {ev.payload}"
            assert "estado" in ev.payload, f"Missing estado in payload: {ev.payload}"
            assert ev.payload["order_id"] == 5
            assert ev.payload["estado"] == "EN_PREPARACION"
            assert isinstance(ev.ts, datetime)

    def test_publish_is_best_effort_does_not_raise(self):
        """
        _publish_order_state_event must not raise even if the publisher.publish() fails.
        """
        from features.orders import service as orders_service

        broken_mock = MagicMock()
        broken_mock.publish.side_effect = RuntimeError("queue exploded")

        with patch("features.websocket.registration._event_publisher", broken_mock):
            try:
                orders_service._publish_order_state_event(pedido_id=1, estado_nuevo="CONFIRMADO")
            except Exception as exc:
                pytest.fail(f"_publish_order_state_event raised unexpectedly: {exc}")
