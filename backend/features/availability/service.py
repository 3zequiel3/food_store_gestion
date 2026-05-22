"""
Ingredient availability service — report, resolve, and query operations (D6, Phase 6).

All multi-table writes run inside the caller's session (injected at construction).
The caller is responsible for committing the session (UoW pattern).
Post-commit events are published best-effort via the injected publisher.

Public API:
  IngredientAvailabilityService(session, publisher=None)
    .report_unavailable(ingrediente_id, reportado_por, pedido_id)
      → sets Ingrediente.activo=False + inserts HistorialDisponibilidadIngrediente row
        → publishes ingredient_unavailable_reported to orders:all
    .resolve_availability(ingrediente_id, resuelto_por)
      → sets Ingrediente.activo=True + bulk-closes all open rows
        → publishes ingredient_availability_restored to kitchen:all
    .get_open_shortages()  → list[HistorialDisponibilidadIngrediente] (resuelto_en IS NULL)
    .get_resolved_history() → list[HistorialDisponibilidadIngrediente] (resuelto_en IS NOT NULL)

Placement rationale: this service belongs to the availability domain, not to websocket
(which is transport only). The websocket router calls this service; the service does NOT
import from features.websocket — direction is transport→service, not the reverse.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, update
from sqlalchemy.orm import Session

from features.availability.models import HistorialDisponibilidadIngrediente
from features.catalog.models import Ingrediente
from features.websocket.contracts import DomainEvent

logger = logging.getLogger(__name__)


class IngredientAvailabilityService:
    """
    Service layer for ingredient kitchen-availability operations.

    The session is injected — the caller owns the transaction boundary.
    The publisher is optional; if None or if publish() raises, the error is
    swallowed (best-effort D6).
    """

    def __init__(
        self,
        session: Session,
        publisher=None,
    ) -> None:
        self._session = session
        self._publisher = publisher

    # ── Report unavailable (cook action) ────────────────────────────────────

    def report_unavailable(
        self,
        *,
        ingrediente_id: int,
        reportado_por: int,
        pedido_id: int,
    ) -> HistorialDisponibilidadIngrediente:
        """
        Mark an ingredient as unavailable.

        Inside the caller's session (UoW):
          1. Set Ingrediente.activo = False.
          2. Insert one HistorialDisponibilidadIngrediente row (resuelto_en=NULL).

        Post-flush: publish ingredient_unavailable_reported to orders:all (best-effort).

        Returns the newly-created history row (before final commit).
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

        # Best-effort publish — after flush so the row has an id
        self._publish_report_event(
            ingrediente_id=ingrediente_id,
            ingrediente_nombre=ing.nombre,
            pedido_id=pedido_id,
            reportado_por=reportado_por,
            reporte_id=history_row.id,
        )

        return history_row

    # ── Resolve availability (admin action) ──────────────────────────────────

    def resolve_availability(
        self,
        *,
        ingrediente_id: int,
        resuelto_por: int,
    ) -> int:
        """
        Resolve an ingredient shortage.

        Inside the caller's session (UoW):
          1. Set Ingrediente.activo = True.
          2. Bulk-close ALL open rows (resuelto_en IS NULL) for this ingredient
             by setting resuelto_en = now() and resuelto_por = admin_id.

        Post-update: publish ingredient_availability_restored to kitchen:all (best-effort).

        Returns the number of rows closed.
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

        # Best-effort publish
        self._publish_restore_event(
            ingrediente_id=ingrediente_id,
            ingrediente_nombre=ing.nombre,
            resuelto_por=resuelto_por,
        )

        logger.debug(
            "resolve_availability: ingrediente_id=%d closed=%d rows",
            ingrediente_id,
            closed_count,
        )
        return closed_count

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

    # ── Private publish helpers (best-effort) ────────────────────────────────

    def _publish_report_event(
        self,
        *,
        ingrediente_id: int,
        ingrediente_nombre: str,
        pedido_id: int,
        reportado_por: int,
        reporte_id: Optional[int],
    ) -> None:
        """Publish ingredient_unavailable_reported to orders:all. Never raises."""
        if self._publisher is None:
            return
        try:
            event = DomainEvent(
                v=1,
                type="ingredient_unavailable_reported",
                topic="orders:all",
                payload={
                    "ingrediente_id": ingrediente_id,
                    "ingrediente_nombre": ingrediente_nombre,
                    "pedido_id": pedido_id,
                    "reportado_por": reportado_por,
                    "reporte_id": reporte_id,
                },
            )
            self._publisher.publish(event)
        except Exception:
            logger.debug(
                "IngredientAvailabilityService: failed to publish ingredient_unavailable_reported "
                "(best-effort, swallowed)",
                exc_info=True,
            )

    def _publish_restore_event(
        self,
        *,
        ingrediente_id: int,
        ingrediente_nombre: str,
        resuelto_por: int,
    ) -> None:
        """Publish ingredient_availability_restored to kitchen:all. Never raises."""
        if self._publisher is None:
            return
        try:
            event = DomainEvent(
                v=1,
                type="ingredient_availability_restored",
                topic="kitchen:all",
                payload={
                    "ingrediente_id": ingrediente_id,
                    "ingrediente_nombre": ingrediente_nombre,
                    "resuelto_por": resuelto_por,
                },
            )
            self._publisher.publish(event)
        except Exception:
            logger.debug(
                "IngredientAvailabilityService: failed to publish ingredient_availability_restored "
                "(best-effort, swallowed)",
                exc_info=True,
            )
