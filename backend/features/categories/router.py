"""
Categories API router — CRUD endpoints for the hierarchical category tree.

Four endpoints:
- ``POST /``           → create category (ADMIN | STOCK)
- ``GET /``            → list tree (public)
- ``PUT /{id}``        → update category (ADMIN | STOCK)
- ``DELETE /{id}``     → soft-delete category (ADMIN | STOCK)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from backend.dependencies import get_uow
from backend.features.auth.dependencies import require_role
from backend.features.categories.schemas import (
    CategoriaCreate,
    CategoriaRead,
    CategoriaTreeNode,
    CategoriaUpdate,
)
from backend.features.categories.service import CategoryService
from backend.shared.unit_of_work import UnitOfWork

router = APIRouter()


@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def crear_categoria(
    payload: CategoriaCreate,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> CategoriaRead:
    """Create a new category.

    Requires ADMIN or STOCK role.
    """
    service = CategoryService(uow)
    cat = service.create(payload)
    uow.commit()
    return CategoriaRead.model_validate(cat)


@router.get("/", response_model=list[CategoriaTreeNode])
async def listar_categorias(
    uow: UnitOfWork = Depends(get_uow),
) -> list[CategoriaTreeNode]:
    """Get the full category tree. Public endpoint (no auth required)."""
    service = CategoryService(uow)
    return service.get_tree()


@router.put("/{categoria_id}", response_model=CategoriaRead)
async def actualizar_categoria(
    categoria_id: int,
    payload: CategoriaUpdate,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> CategoriaRead:
    """Update a category. Requires ADMIN or STOCK role."""
    service = CategoryService(uow)
    cat = service.update(categoria_id, payload)
    uow.commit()
    return CategoriaRead.model_validate(cat)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_categoria(
    categoria_id: int,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Soft-delete a category. Requires ADMIN or STOCK role."""
    service = CategoryService(uow)
    service.delete(categoria_id)
    uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
