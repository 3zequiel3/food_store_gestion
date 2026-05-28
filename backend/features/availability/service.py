"""
Ingredient availability service — report, resolve, and query operations (D6, Phase 6).

All multi-table writes run inside the caller's session (injected at construction).
The caller is responsible for committing the session (UoW pattern).
Post-commit events are published best-effort by the ROUTER (caller), NOT here.

Public API:
  IngredientAvailabilityService(session)
    .report_unavailable(ingrediente_id, reportado_por, pedido_id)
      → sets Ingrediente.activo=False + inserts HistorialDisponibilidadIngrediente row
      → returns ReportResult DTO (used by router to publish post-commit)
    .resolve_availability(ingrediente_id, resuelto_por)
      → sets Ingrediente.activo=True + bulk-closes all open rows
      → returns ResolveResult DTO (used by router to publish post-commit)
    .get_open_shortages()  → list[HistorialDisponibilidadIngrediente]
    .get_resolved_history() → list[HistorialDisponibilidadIngrediente]

Publish helpers (_publish_report_event, _publish_restore_event) are kept as
module-level functions — the router imports and calls them AFTER the UoW exits.
The topic/payload contract has a single home (this module).

Design: Decision 1 — publish-after-commit (design.md).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, update
from sqlalchemy.orm import Session

from features.availability.models import HistorialDisponibilidadIngrediente
from features.catalog.models import Ingrediente
from features.websocket.contracts import DomainEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result DTOs — carry the data needed to publish events post-commit
# ---------------------------------------------------------------------------


@dataclass
class ReportResult:
    """
    DTO returned by report_unavailable().

    Contains enough data for the router to call _publish_report_event()
    after the UoW commits, without reopening the session.
    """
    ingrediente_id: int
    ingrediente_nombre: str
    pedido_id: int
    reportado_por: int
    history_id: Optional[int]


@dataclass
class ResolveResult:
    """
    DTO returned by resolve_availability().

    Contains enough data for the router to call _publish_restore_event()
    after the UoW commits, without reopening the session.
    """
    ingrediente_id: int
    ingrediente_nombre: str
    resolved_count: int
    resuelto_por: int
    resolved_at: datetime


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class IngredientAvailabilityService:
    """
    Service layer for ingredient kitchen-availability operations.

    The session is injected — the caller owns the transaction boundary.
    This service does NOT publish events. The caller (router) publishes
    using the DTO returned by each method, AFTER the UoW commits.

    Design: Decision 1 (design.md) — publish-after-commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Report unavailable (cook action) ────────────────────────────────────

    def report_unavailable(
        self,
        *,
        ingrediente_id: int,
        reportado_por: int,
        pedido_id: int,
    ) -> ReportResult:
        """
        Mark an ingredient as unavailable.

        Inside the caller's session (UoW):
          1. Set Ingrediente.activo = False.
          2. Insert one HistorialDisponibilidadIngrediente row (resuelto_en=NULL).

        Returns ReportResult DTO. The router calls _publish_report_event()
        with this DTO AFTER the UoW commits.
        """
        ing = self._session.get(Ingrediente, ingrediente_id)
        if ing is None:
            raise ValueError(f"Ingrediente not found: id={ingrediente_id}")

        # 1. Toggle availability flag
        ing.activo = False

        # 2. Append the history row
        history_row = HistorialDisponibilidadIngrediente(
            ingrediente_id=ingrediente_id,
            reportado_por=reportado_por,
            pedido_id=pedido_id,
            resuelto_en=None,
            resuelto_por=None,
        )
        self._session.add(history_row)
        self._session.flush()

        return ReportResult(
            ingrediente_id=ingrediente_id,
            ingrediente_nombre=ing.nombre,
            pedido_id=pedido_id,
            reportado_por=reportado_por,
            history_id=history_row.id,
        )

    # ── Resolve availability (admin action) ──────────────────────────────────

    def resolve_availability(
        self,
        *,
        ingrediente_id: int,
        resuelto_por: int,
    ) -> ResolveResult:
        """
        Resolve an ingredient shortage.

        Inside the caller's session (UoW):
          1. Set Ingrediente.activo = True.
          2. Bulk-close ALL open rows (resuelto_en IS NULL) for this ingredient
             by setting resuelto_en = now() and resuelto_por = admin_id.

        Returns ResolveResult DTO. The router calls _publish_restore_event()
        with this DTO AFTER the UoW commits.
        """
        ing = self._session.get(Ingrediente, ingrediente_id)
        if ing is None:
            raise ValueError(f"Ingrediente not found: id={ingrediente_id}")

        # 1. Restore availability flag
        ing.activo = True

        # 2. Bulk-close all pending rows
        now = datetime.now(timezone.utc)
        result = self._session.execute(
            update(HistorialDisponibilidadIngrediente)
            .where(
                and_(
                    HistorialDisponibilidadIngrediente.ingrediente_id == ingrediente_id,
                    HistorialDisponibilidadIngrediente.resuelto_en.is_(None),
                )
            )
            .values(resuelto_en=now, resuelto_por=resuelto_por)
        )
        closed_count = result.rowcount

        self._session.flush()

        logger.debug(
            "resolve_availability: ingrediente_id=%d closed=%d rows",
            ingrediente_id,
            closed_count,
        )

        return ResolveResult(
            ingrediente_id=ingrediente_id,
            ingrediente_nombre=ing.nombre,
            resolved_count=closed_count,
            resuelto_por=resuelto_por,
            resolved_at=now,
        )

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_open_shortages(self) -> list[HistorialDisponibilidadIngrediente]:
        """
        Return all pending shortage reports (resuelto_en IS NULL).

        These feed the admin "Faltantes" view and the navbar inbox count.
        """
        return (
            self._session.query(HistorialDisponibilidadIngrediente)
            .filter(HistorialDisponibilidadIngrediente.resuelto_en.is_(None))
            .order_by(HistorialDisponibilidadIngrediente.creado_en.asc())
            .all()
        )

    def get_resolved_history(self) -> list[HistorialDisponibilidadIngrediente]:
        """
        Return all resolved shortage reports (resuelto_en IS NOT NULL).

        These feed the admin audit/history view.
        """
        return (
            self._session.query(HistorialDisponibilidadIngrediente)
            .filter(HistorialDisponibilidadIngrediente.resuelto_en.isnot(None))
            .order_by(HistorialDisponibilidadIngrediente.resuelto_en.desc())
            .all()
        )


# ---------------------------------------------------------------------------
# Module-level publish helpers — called by the router POST-COMMIT
# Topic/payload contract lives here (single home).
# ---------------------------------------------------------------------------


def _publish_report_event(
    publisher,
    *,
    dto: ReportResult,
) -> None:
    """
    Publish ingredient_unavailable_reported to orders:all.

    Called by the router AFTER `with UnitOfWork():` exits (post-commit).
    Never raises — best-effort.
    """
    if publisher is None:
        return
    try:
        event = DomainEvent(
            v=1,
            type="ingredient_unavailable_reported",
            topic="orders:all",
            payload={
                "ingrediente_id": dto.ingrediente_id,
                "ingrediente_nombre": dto.ingrediente_nombre,
                "pedido_id": dto.pedido_id,
                "reportado_por": dto.reportado_por,
                "reporte_id": dto.history_id,
            },
        )
        publisher.publish(event)
    except Exception:
        logger.debug(
            "_publish_report_event: failed to publish ingredient_unavailable_reported "
            "(best-effort, swallowed)",
            exc_info=True,
        )


def _publish_restore_event(
    publisher,
    *,
    dto: ResolveResult,
) -> None:
    """
    Publish ingredient_availability_restored to kitchen:all AND orders:all.

    Fan-out:
      - kitchen:all  → cocina shows the toast and unblocks affected pedidos.
      - orders:all   → admin's faltantes view refreshes its list without
                       a manual reload.

    Called by the router AFTER `with UnitOfWork():` exits (post-commit).
    Never raises — best-effort.
    """
    if publisher is None:
        return
    payload = {
        "ingrediente_id": dto.ingrediente_id,
        "ingrediente_nombre": dto.ingrediente_nombre,
        "resuelto_por": dto.resuelto_por,
    }
    for topic in ("kitchen:all", "orders:all"):
        try:
            event = DomainEvent(
                v=1,
                type="ingredient_availability_restored",
                topic=topic,
                payload=payload,
            )
            publisher.publish(event)
        except Exception:
            logger.debug(
                "_publish_restore_event: failed to publish "
                "ingredient_availability_restored on topic=%s "
                "(best-effort, swallowed)",
                topic,
                exc_info=True,
            )
