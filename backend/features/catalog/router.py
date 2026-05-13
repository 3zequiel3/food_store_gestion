"""
Catalog feature router.

Exposes reference data endpoints (payment methods, order states, etc.)
for client-side selectors. All endpoints are read-only.
"""

from typing import List

from fastapi import APIRouter, Depends, status

from backend.features.auth.dependencies import get_current_user
from backend.features.catalog.schemas import FormaPagoRead
from backend.features.catalog.service import listar_formas_pago
from backend.features.users.models import Usuario

router = APIRouter()


@router.get(
    "/formas-pago",
    response_model=List[FormaPagoRead],
    status_code=status.HTTP_200_OK,
    summary="Listar formas de pago habilitadas",
    description=(
        "Retorna todas las formas de pago con habilitada=True. "
        "Requiere autenticación JWT. Usado por el selector de pago en checkout."
    ),
)
async def get_formas_pago(
    current_user: Usuario = Depends(get_current_user),
) -> List[FormaPagoRead]:
    """
    GET /api/v1/formas-pago — list enabled payment methods.

    Authentication: Bearer JWT required (401 if missing/invalid).
    Authorization: Any authenticated user can list payment methods.

    Returns: List of FormaPagoRead ordered by id ascending.
    """
    formas = listar_formas_pago()
    return [FormaPagoRead.model_validate(f) for f in formas]
