"""
Products API router — 11 endpoints for the product catalog.

Endpoint groups:
1. CRUD base:
   - POST   /              → create product         (ADMIN | STOCK)
   - GET    /              → list paginated          (public, default disponible=True)
   - GET    /{id}          → product detail          (public)
   - PUT    /{id}          → update product          (ADMIN | STOCK)
   - DELETE /{id}          → soft-delete product     (ADMIN | STOCK)

2. Availability & stock patches:
   - PATCH  /{id}/disponibilidad  → toggle availability (ADMIN | STOCK)
   - PATCH  /{id}/stock           → set absolute stock  (ADMIN | STOCK)

3. Category M:N:
   - PUT    /{id}/categorias → replace category set  (ADMIN | STOCK)

4. Ingredient M:N:
   - GET    /{id}/ingredientes      → list associations  (public)
   - POST   /{id}/ingredientes      → add association    (ADMIN | STOCK)
   - DELETE /{id}/ingredientes/{ing_id} → remove assoc  (ADMIN | STOCK)

Prefix is /api/v1/productos (configured in main.py — D12 in design.md).
All errors flow from the service via typed domain exceptions; no raw
HTTPException is raised here. The global handlers in main.py map them to
RFC 7807 Problem Details.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status

from backend.features.auth.dependencies import get_optional_user, require_role
from backend.features.users.models import Usuario
from backend.features.products.schemas import (
    AsociarIngrediente,
    CategoriaRead,
    IngredienteAsociadoRead,
    PaginatedProductos,
    PatchDisponibilidad,
    PatchStock,
    ProductoCreate,
    ProductoDetail,
    ProductoRead,
    ProductoUpdate,
    SetCategorias,
)
from backend.features.products.service import ProductService

router = APIRouter()


# ===========================================================================
# 1. CRUD base
# ===========================================================================


@router.post("/", response_model=ProductoRead, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    payload: ProductoCreate,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoRead:
    """Create a new product.

    Optionally associates categories if ``categoria_ids`` is provided in body.
    Requires ADMIN or STOCK role.
    """
    service = ProductService()
    producto = service.create(payload)
    return ProductoRead.model_validate(producto)


@router.get("/", response_model=PaginatedProductos)
async def listar_productos(
    page: int = Query(1, ge=1, description="1-based page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    categoria_id: int | None = Query(None, description="Filter by category ID"),
    search: str | None = Query(None, description="Case-insensitive substring match on nombre"),
    disponible: bool | None = Query(None, description="Filter by availability (default: true)"),
    excluir_alergenos: bool = Query(False, description="Exclude products with non-removable allergens"),
    incluir_eliminados: bool = Query(
        False,
        description="Include soft-deleted products (ADMIN only, RN-CA10). Ignored for other roles.",
    ),
    current_user: Optional[Usuario] = Depends(get_optional_user),
) -> PaginatedProductos:
    """List products with pagination and optional filters.

    Public endpoint — no authentication required for standard catalog access.

    Default behaviour when ``disponible`` is not specified: only available
    products are returned (disponible=true), per RN-CA08 (public catalog).
    Pass ``?disponible=false`` explicitly to retrieve unavailable products.

    The ``incluir_eliminados`` flag is only effective for ADMIN users (RN-CA10).
    For other roles or unauthenticated requests it is silently ignored.
    """
    # Apply RN-CA08 default: public catalog shows only available products
    if disponible is None:
        disponible = True

    service = ProductService()
    items, total = service.list_paginated(
        page=page,
        limit=limit,
        categoria_id=categoria_id,
        search=search,
        disponible=disponible,
        excluir_alergenos=excluir_alergenos,
        current_user=current_user,
        incluir_eliminados=incluir_eliminados,
    )
    return PaginatedProductos(
        items=[ProductoRead.model_validate(p) for p in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{producto_id}", response_model=ProductoDetail)
async def obtener_producto(
    producto_id: int,
) -> ProductoDetail:
    """Get full product detail with categories and ingredients.

    Public endpoint — no authentication required.
    Returns 404 for soft-deleted or non-existent products.
    """
    service = ProductService()
    producto, categorias, ingredientes_with_flag = service.get_detail(producto_id)

    return ProductoDetail(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        categorias=[CategoriaRead.model_validate(c) for c in categorias],
        ingredientes=[
            IngredienteAsociadoRead(
                id=ing.id,
                nombre=ing.nombre,
                es_alergeno=ing.es_alergeno,
                es_removible=removible,
            )
            for (ing, removible) in ingredientes_with_flag
        ],
    )


@router.put("/{producto_id}", response_model=ProductoRead)
async def actualizar_producto(
    producto_id: int,
    payload: ProductoUpdate,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoRead:
    """Partially update a product.

    Omitted fields are preserved. Requires ADMIN or STOCK role.
    Returns 404 for soft-deleted or non-existent products.
    """
    service = ProductService()
    producto = service.update(producto_id, payload)
    return ProductoRead.model_validate(producto)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_producto(
    producto_id: int,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Soft-delete a product.

    Requires ADMIN or STOCK role. Pivot rows (categories, ingredients) are
    NOT modified — the product stops appearing in the catalog naturally.
    Returns 204 on success, 404 if not found or already deleted.
    """
    service = ProductService()
    service.delete(producto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# 2. Patches — availability and stock
# ===========================================================================


@router.patch("/{producto_id}/disponibilidad", response_model=ProductoRead)
async def patch_disponibilidad(
    producto_id: int,
    payload: PatchDisponibilidad,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoRead:
    """Toggle product availability.

    Requires ADMIN or STOCK role.
    disponible=false hides the product from the public catalog.
    disponible=true makes it visible again.
    """
    service = ProductService()
    producto = service.set_disponibilidad(producto_id, payload.disponible)
    return ProductoRead.model_validate(producto)


@router.patch("/{producto_id}/stock", response_model=ProductoRead)
async def patch_stock(
    producto_id: int,
    payload: PatchStock,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoRead:
    """Set absolute stock quantity.

    Requires ADMIN or STOCK role.
    Replaces the current stock value (D5: absolute set, not delta).
    """
    service = ProductService()
    producto = service.set_stock(producto_id, payload.stock_cantidad)
    return ProductoRead.model_validate(producto)


# ===========================================================================
# 3. Category M:N
# ===========================================================================


@router.put("/{producto_id}/categorias", response_model=ProductoDetail)
async def set_categorias(
    producto_id: int,
    payload: SetCategorias,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoDetail:
    """Replace the full category set for a product (US-016).

    Requires ADMIN or STOCK role.
    Pass an empty list to remove all categories.
    Returns the updated product detail with refreshed associations.
    """
    service = ProductService()
    producto, categorias, ingredientes_with_flag = service.set_categorias(
        producto_id, payload.categoria_ids
    )
    return ProductoDetail(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        categorias=[CategoriaRead.model_validate(c) for c in categorias],
        ingredientes=[
            IngredienteAsociadoRead(
                id=ing.id,
                nombre=ing.nombre,
                es_alergeno=ing.es_alergeno,
                es_removible=removible,
            )
            for (ing, removible) in ingredientes_with_flag
        ],
    )


# ===========================================================================
# 4. Ingredient M:N
# ===========================================================================


@router.get(
    "/{producto_id}/ingredientes",
    response_model=list[IngredienteAsociadoRead],
)
async def listar_ingredientes_producto(
    producto_id: int,
) -> list[IngredienteAsociadoRead]:
    """List active ingredient associations for a product.

    Public endpoint — no authentication required.
    Each item includes the es_removible flag from the pivot table.
    Returns 404 if the product is not found or soft-deleted.
    """
    service = ProductService()
    result = service.list_ingredientes(producto_id)
    return [
        IngredienteAsociadoRead(
            id=ing.id,
            nombre=ing.nombre,
            es_alergeno=ing.es_alergeno,
            es_removible=removible,
        )
        for (ing, removible) in result
    ]


@router.post(
    "/{producto_id}/ingredientes",
    response_model=IngredienteAsociadoRead,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_ingrediente(
    producto_id: int,
    payload: AsociarIngrediente,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> IngredienteAsociadoRead:
    """Associate an ingredient with a product.

    Requires ADMIN or STOCK role.
    Returns 409 if the association already exists and is active.
    Reactivates soft-deleted associations (updating es_removible).
    """
    service = ProductService()
    pi, result = service.add_ingrediente(
        producto_id, payload.ingrediente_id, payload.es_removible
    )

    # Find the ingredient in the updated list
    for ing, removible in result:
        if ing.id == payload.ingrediente_id:
            return IngredienteAsociadoRead(
                id=ing.id,
                nombre=ing.nombre,
                es_alergeno=ing.es_alergeno,
                es_removible=removible,
            )

    # Fallback: build from pivot row (should not be reached in normal flow)
    return IngredienteAsociadoRead(
        id=payload.ingrediente_id,
        nombre="",
        es_alergeno=False,
        es_removible=pi.es_removible,
    )


@router.delete(
    "/{producto_id}/ingredientes/{ingrediente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_ingrediente_producto(
    producto_id: int,
    ingrediente_id: int,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Remove (soft-delete) an ingredient association from a product.

    Requires ADMIN or STOCK role.
    The ingredient row itself is NOT modified — only the pivot is soft-deleted.
    Returns 404 if the association is not found or already removed.
    """
    service = ProductService()
    service.remove_ingrediente(producto_id, ingrediente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
