"""
Ingredients API router — CRUD endpoints for ingredients.

Five endpoints:
- ``POST /``              → create ingredient (ADMIN | STOCK)
- ``GET /``               → list ingredients paginated (public)
- ``GET /{id}``           → get ingredient by id (public)
- ``PUT /{id}``           → update ingredient (ADMIN | STOCK)
- ``DELETE /{id}``        → soft-delete ingredient (ADMIN | STOCK)

All error responses use RFC 7807 via the domain exceptions raised in the
service — no raw HTTPException is raised here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from backend.dependencies import get_uow
from backend.features.auth.dependencies import require_role
from backend.features.ingredients.schemas import (
    IngredienteCreate,
    IngredienteRead,
    IngredienteUpdate,
    PaginatedIngredientes,
)
from backend.features.ingredients.service import IngredientService
from backend.shared.unit_of_work import UnitOfWork

router = APIRouter()


@router.post("/", response_model=IngredienteRead, status_code=status.HTTP_201_CREATED)
async def crear_ingrediente(
    payload: IngredienteCreate,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> IngredienteRead:
    """Create a new ingredient.

    Requires ADMIN or STOCK role. Returns 409 if nombre already exists
    (including soft-deleted ingredients).
    """
    service = IngredientService(uow)
    ing = service.create(payload)
    uow.commit()
    return IngredienteRead.model_validate(ing)


@router.get("/", response_model=PaginatedIngredientes)
async def listar_ingredientes(
    page: int = Query(1, ge=1, description="1-based page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    es_alergeno: bool | None = Query(None, description="Filter by allergen flag"),
    uow: UnitOfWork = Depends(get_uow),
) -> PaginatedIngredientes:
    """List active ingredients with optional filtering and pagination.

    Public endpoint — no authentication required.
    Soft-deleted ingredients are excluded automatically.
    """
    service = IngredientService(uow)
    items, total = service.list_paginated(
        page=page, limit=limit, es_alergeno=es_alergeno
    )
    return PaginatedIngredientes(
        items=[IngredienteRead.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{ingrediente_id}", response_model=IngredienteRead)
async def obtener_ingrediente(
    ingrediente_id: int,
    uow: UnitOfWork = Depends(get_uow),
) -> IngredienteRead:
    """Get a single active ingredient by ID.

    Public endpoint — no authentication required.
    Returns 404 for soft-deleted or non-existent ingredients.
    """
    service = IngredientService(uow)
    ing = service.get_by_id(ingrediente_id)
    return IngredienteRead.model_validate(ing)


@router.put("/{ingrediente_id}", response_model=IngredienteRead)
async def actualizar_ingrediente(
    ingrediente_id: int,
    payload: IngredienteUpdate,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> IngredienteRead:
    """Partially update an ingredient.

    Requires ADMIN or STOCK role. Omitted fields are preserved.
    Returns 404 for soft-deleted or non-existent ingredients.
    """
    service = IngredientService(uow)
    ing = service.update(ingrediente_id, payload)
    uow.commit()
    return IngredienteRead.model_validate(ing)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_ingrediente(
    ingrediente_id: int,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Soft-delete an ingredient.

    Requires ADMIN or STOCK role. No guard is applied for associated
    products — US-014 is satisfied by the soft delete itself.
    Returns 204 on success, 404 if not found or already deleted.
    """
    service = IngredientService(uow)
    service.delete(ingrediente_id)
    uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
