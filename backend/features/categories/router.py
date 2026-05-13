"""
Categories API router — CRUD endpoints for the hierarchical category tree.

Four endpoints:
- ``POST /``           → create category (ADMIN | STOCK)
- ``GET /``            → list tree or flat leaves (public)
  - Without params or solo_hojas=false: full nested tree (CategoriaTreeNode)
  - ?solo_hojas=true: flat list of leaf categories (CategoriaRead, D7)
- ``PUT /{id}``        → update category (ADMIN | STOCK)
- ``DELETE /{id}``     → soft-delete category (ADMIN | STOCK)
"""

from __future__ import annotations

from typing import Union

from fastapi import APIRouter, Depends, Query, Response, status

from features.auth.dependencies import require_role
from features.categories.schemas import (
    CategoriaCreate,
    CategoriaRead,
    CategoriaTreeNode,
    CategoriaUpdate,
)
from features.categories.service import CategoryService

router = APIRouter()


@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def crear_categoria(
    payload: CategoriaCreate,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> CategoriaRead:
    """Create a new category.

    Requires ADMIN or STOCK role.
    When ``padre_id`` is provided, the parent category must have zero active
    product associations — block-on-promote guard (D6).
    """
    service = CategoryService()
    cat = service.create(payload)
    return CategoriaRead.model_validate(cat)


@router.get("/", response_model=Union[list[CategoriaRead], list[CategoriaTreeNode]])
async def listar_categorias(
    solo_hojas: bool = Query(
        False,
        description=(
            "When true, returns a flat list of active leaf categories "
            "(no subcategorias field), sorted alphabetically by nombre. "
            "Intended for admin product-assignment dropdowns (D7). "
            "When false (default), returns the full nested tree."
        ),
    ),
) -> list[CategoriaRead] | list[CategoriaTreeNode]:
    """Get categories. Public endpoint (no auth required).

    Two response modes controlled by ``solo_hojas``:
    - **false** (default): Full nested tree of ``CategoriaTreeNode`` with
      ``subcategorias`` list populated recursively.
    - **true**: Flat list of ``CategoriaRead`` containing only leaf categories
      (active categories with zero non-deleted children), sorted A→Z.
    """
    service = CategoryService()
    if solo_hojas:
        return service.list_leaves()
    return service.get_tree()


@router.put("/{categoria_id}", response_model=CategoriaRead)
async def actualizar_categoria(
    categoria_id: int,
    payload: CategoriaUpdate,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> CategoriaRead:
    """Update a category. Requires ADMIN or STOCK role."""
    service = CategoryService()
    cat = service.update(categoria_id, payload)
    return CategoriaRead.model_validate(cat)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_categoria(
    categoria_id: int,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Soft-delete a category. Requires ADMIN or STOCK role."""
    service = CategoryService()
    service.delete(categoria_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
