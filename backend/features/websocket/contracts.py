"""
WebSocket versioned event contract and EventPublisher port.

Design: D2 — EventPublisher as a Protocol so the order domain depends on this
port, not on a concrete transport implementation.

Versioned wire format:
  {
    "v": 1,
    "type": "order_state_changed",
    "topic": "kitchen:all",
    "payload": { ... },
    "ts": "2026-05-21T12:00:00+00:00"
  }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


@dataclass
class DomainEvent:
    """
    Versioned domain event — the unit flowing through the EventPublisher port.

    Fields:
      v       — contract version (always 1 for this generation)
      type    — domain event type (e.g. "order_state_changed")
      topic   — routing key for the connection manager (e.g. "kitchen:all", "order:42")
      payload — arbitrary dict; shape depends on `type`
      ts      — UTC timestamp when the event was created
    """

    v: int
    type: str
    topic: str
    payload: dict[str, Any]
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the versioned wire format sent over the WebSocket."""
        return {
            "v": self.v,
            "type": self.type,
            "topic": self.topic,
            "payload": self.payload,
            "ts": self.ts.isoformat(),
        }


@runtime_checkable
class EventPublisher(Protocol):
    """
    Port: publish a domain event.

    Contract:
    - MUST be best-effort: never raises to the caller under any circumstance.
    - MUST NOT block the caller (sync-safe, non-blocking).
    - Implementation detail: InProcessEventPublisher enqueues onto an asyncio.Queue
      drained by the broadcast task (see publisher.py).
    """

    def publish(self, event: DomainEvent) -> None:
        """Enqueue `event` for broadcast. Best-effort, never raises."""
        ...
