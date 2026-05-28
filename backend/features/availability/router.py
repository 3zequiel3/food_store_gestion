"""
Admin ingredient availability REST endpoints — D6, Phase 6.

Prefix (registered in main.py): /api/v1/availability
All endpoints require ADMIN role.

Routes:
  GET  /faltantes
    → list open shortages (resuelto_en IS NULL) from HistorialDisponibilidadIngrediente.
    → used by the admin navbar inbox + "Faltantes" view.

  POST /faltantes/{ingrediente_id}/resolver
    → set Ingrediente.activo=True + bulk-close all open rows for that ingredient.
    → publishes ingredient_availability_restored to kitchen:all (best-effort, post-commit).
    → RBAC: ADMIN only.

Design: Decision 1 (design.md) — publish helpers called AFTER `with UnitOfWork():` exits.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import selectinload

from features.auth.dependencies import require_role
from features.availability.models import HistorialDisponibilidadIngrediente
from features.availability.schemas import (
    ResolveRequest,
    ResolveResponse,
    ShortageReportItem,
)
from features.availability.service import (
    IngredientAvailabilityService,
    _publish_restore_event,
)
from features.users.models import Usuario
from features.websocket.registration import get_event_publisher
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /faltantes — list open shortages (admin inbox / Faltantes view)
# ---------------------------------------------------------------------------


@router.get(
    "/faltantes",
    response_model=list[ShortageReportItem],
    summary="Listar faltantes de ingredientes (Admin)",
    description=(
        "Retorna todos los reportes de ingredientes no disponibles cuyo "
        "resuelto_en IS NULL (pendientes). Requiere rol ADMIN."
    ),
)
def list_faltantes(
    current_user: Usuario = Depends(require_role("ADMIN")),
) -> list[ShortageReportItem]:
    """
    Return all open ingredient-shortage reports.

    Each row includes ingrediente_nombre when the ingrediente relationship
    is loaded. We use a direct session (read-only) to eager-load the ingredient.
    """
    import shared.unit_of_work as _uow_mod

    session = _uow_mod.get_session_factory()()
    try:
        rows = (
            session.query(HistorialDisponibilidadIngrediente)
            .options(selectinload(HistorialDisponibilidadIngrediente.ingrediente))
            .filter(HistorialDisponibilidadIngrediente.resuelto_en.is_(None))
            .order_by(HistorialDisponibilidadIngrediente.creado_en.asc())
            .all()
        )

        return [
            ShortageReportItem(
                id=row.id,
                ingrediente_id=row.ingrediente_id,
                ingrediente_nombre=(
                    row.ingrediente.nombre if row.ingrediente else None
                ),
                reportado_por=row.reportado_por,
                pedido_id=row.pedido_id,
                creado_en=row.creado_en,
                resuelto_en=row.resuelto_en,
                resuelto_por=row.resuelto_por,
            )
            for row in rows
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /faltantes/{ingrediente_id}/resolver — resolve a shortage
# ---------------------------------------------------------------------------


@router.post(
    "/faltantes/{ingrediente_id}/resolver",
    response_model=ResolveResponse,
    summary="Resolver faltante de ingrediente (Admin)",
    description=(
        "Marca el ingrediente como disponible (activo=True) y cierra todos los "
        "reportes pendientes para ese ingrediente. Emite ingredient_availability_restored "
        "al canal de cocina (best-effort, post-commit). Requiere rol ADMIN."
    ),
)
def resolver_faltante(
    ingrediente_id: int,
    body: ResolveRequest = None,
    current_user: Usuario = Depends(require_role("ADMIN")),
) -> ResolveResponse:
    """
    Resolve an ingredient shortage.

    Inside ONE UoW:
      1. Set Ingrediente.activo = True.
      2. Bulk-close all open rows (resuelto_en IS NULL) for the ingredient.

    AFTER the UoW exits (commits): publish ingredient_availability_restored
    to kitchen:all and orders:all (best-effort, Decision 1 — design.md).
    """
    publisher = get_event_publisher()

    with UnitOfWork() as uow:
        svc = IngredientAvailabilityService(session=uow.session)
        result_dto = svc.resolve_availability(
            ingrediente_id=ingrediente_id,
            resuelto_por=current_user.id,
        )
    # UoW exits here → commit happens → publish post-commit (Decision 1)
    _publish_restore_event(publisher, dto=result_dto)

    logger.info(
        "resolver_faltante: admin_id=%d resolved ingrediente_id=%d (%d rows closed, accion=%r)",
        current_user.id,
        ingrediente_id,
        result_dto.resolved_count,
        (body.accion if body else "solucionado"),
    )

    return ResolveResponse(
        ok=True,
        ingrediente_id=ingrediente_id,
        rows_closed=result_dto.resolved_count,
    )
