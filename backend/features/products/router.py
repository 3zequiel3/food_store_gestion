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

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

from features.auth.dependencies import get_optional_user, require_role
from features.users.models import Usuario
from features.products.schemas import (
    AsociarIngrediente,
    CategoriaRead,
    ImagenOrden,
    ImagenRead,
    ImagenUrl,
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
from features.products.service import ProductService
from shared.storage import StorageService

router = APIRouter()

_storage = StorageService()


def _imagen_to_read_with_presigned(img) -> ImagenRead:
    """Convert a ProductoImagen to ImagenRead, resolving URL via presigned or direct."""
    return ImagenRead(
        id=img.id,
        url=_storage.product_image_url(img.url),
        orden=img.orden,
        es_primaria=img.es_primaria,
    )


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
    return ProductoRead(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        imagenes=[],
    )


@router.get("/", response_model=PaginatedProductos)
async def listar_productos(
    page: int = Query(1, ge=1, description="1-based page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    categoria_id: int | None = Query(
        None,
        description=(
            "Filter by category ID — includes products in this category and "
            "any active descendant categories (resolved via recursive CTE, D1)."
        ),
    ),
    search: str | None = Query(
        None, description="Case-insensitive substring match on nombre"
    ),
    disponible: bool | None = Query(
        None, description="Filter by availability (default: true)"
    ),
    excluir_alergenos: bool = Query(
        False, description="Exclude products with non-removable allergens"
    ),
    excluir_alergeno_ids: list[int] = Query(
        default=[],
        description=(
            "Exclude products that have at least one non-removable ingredient "
            "whose id is in this list (D2). Repeat the param for multiple ids. "
            "Empty / omitted = no-op. Compatible with excluir_alergenos=true (AND)."
        ),
    ),
    sin_categoria: bool = Query(
        False,
        description=(
            "If true, return only products with zero active category associations (D5). "
            "Useful for the admin 'uncategorized products' view."
        ),
    ),
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

    ``categoria_id`` now resolves descendants recursively via a CTE (D1).
    ``excluir_alergeno_ids`` excludes products with specific non-removable
    ingredients by ID list (D2). Combine with ``excluir_alergenos=true`` for
    AND semantics.
    ``sin_categoria=true`` restricts results to uncategorized products (D5).

    The ``incluir_eliminados`` flag is only effective for ADMIN users (RN-CA10).
    For other roles or unauthenticated requests it is silently ignored.
    """
    # Apply RN-CA08 default: public catalog shows only available products
    if disponible is None:
        disponible = True

    service = ProductService()
    items, total, images_by_pid = service.list_with_images(
        page=page,
        limit=limit,
        categoria_id=categoria_id,
        search=search,
        disponible=disponible,
        excluir_alergenos=excluir_alergenos,
        excluir_alergeno_ids=excluir_alergeno_ids,
        sin_categoria=sin_categoria,
        current_user=current_user,
        incluir_eliminados=incluir_eliminados,
    )
    return PaginatedProductos(
        items=[
            ProductoRead(
                id=p.id,
                nombre=p.nombre,
                descripcion=p.descripcion,
                precio=p.precio,
                stock_cantidad=p.stock_cantidad,
                disponible=p.disponible,
                imagen_url=p.imagen_url,
                creado_en=p.creado_en,
                actualizado_en=p.actualizado_en,
                imagenes=[
                    _imagen_to_read_with_presigned(img)
                    for img in images_by_pid.get(p.id, [])
                ],
            )
            for p in items
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/imagenes/{image_path:path}",
    response_class=StreamingResponse,
)
def obtener_imagen_producto(image_path: str) -> StreamingResponse:
    """Serve a stored product image via backend proxy.

    Active when STORAGE=local (dev). When STORAGE=s3, images are served
    via presigned URLs directly from the Railway bucket (avoids service egress).
    """
    stream, content_type = StorageService().open_product_image(image_path)
    return StreamingResponse(stream, media_type=content_type)


class PresignedUploadRequest(BaseModel):
    """Request body for presigned upload generation."""

    content_type: str = "image/jpeg"


@router.post("/{producto_id}/imagenes/presigned-url")
async def obtener_presigned_url(
    producto_id: int,
    payload: PresignedUploadRequest = PresignedUploadRequest(),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> dict:
    """Generate a presigned POST for direct client-to-S3 upload.

    Returns { url, fields } that the frontend uses to POST a file directly
    to the S3 bucket without going through the backend.
    """
    # Verify product exists
    ProductService().get_by_id(producto_id)
    return StorageService().presign_upload(producto_id, payload.content_type)


@router.post(
    "/{producto_id}/imagen",
    response_model=ProductoRead,
    status_code=status.HTTP_200_OK,
)
async def subir_imagen_producto(
    producto_id: int,
    file: UploadFile = File(...),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ProductoRead:
    """Upload and assign a product image.

    Storage is selected by the `STORAGE` env var:
    - `local`: backend/uploads/productos/<producto_id>/...
    - `s3`: configured S3-compatible bucket.

    Also creates a ProductoImagen row for backward compatibility migration.
    """
    service = ProductService()
    service.get_by_id(producto_id)

    imagen_url = await StorageService().save_product_image(producto_id, file)
    producto = service.update(producto_id, ProductoUpdate(imagen_url=imagen_url))

    # Also create a ProductoImagen row
    try:
        service.add_imagen_from_url(producto_id, imagen_url)
    except Exception:
        pass  # Non-critical — legacy compat, don't fail the request

    return ProductoRead(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        imagenes=[],
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

    # Get images from the relationship
    imagenes = [img for img in producto.imagenes if img.eliminado_en is None]
    imagenes.sort(key=lambda x: (x.orden, x.id))

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
        imagenes=[_imagen_to_read_with_presigned(img) for img in imagenes],
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
    return ProductoRead(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        imagenes=[],
    )


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
    return ProductoRead(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        imagenes=[],
    )


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
    return ProductoRead(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        precio=producto.precio,
        stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible,
        imagen_url=producto.imagen_url,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
        imagenes=[],
    )


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

    imagenes = [img for img in producto.imagenes if img.eliminado_en is None]
    imagenes.sort(key=lambda x: (x.orden, x.id))

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
        imagenes=[_imagen_to_read_with_presigned(img) for img in imagenes],
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


# ===========================================================================
# 5. Image CRUD
# ===========================================================================


@router.post(
    "/{producto_id}/imagenes",
    response_model=ImagenRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_imagen(
    producto_id: int,
    file: UploadFile = File(...),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ImagenRead:
    """Upload a new image for a product."""
    service = ProductService()
    # Verify product exists
    service.get_by_id(producto_id)

    # Save file via StorageService (async)
    url = await StorageService().save_product_image(producto_id, file)

    # Create DB row
    img = service.add_imagen_from_url(producto_id, url)
    return _imagen_to_read_with_presigned(img)


@router.post(
    "/{producto_id}/imagenes/url",
    response_model=ImagenRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_imagen_url(
    producto_id: int,
    payload: ImagenUrl,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ImagenRead:
    """Add an image by URL for a product."""
    service = ProductService()
    img = service.add_imagen_from_url(producto_id, payload.url)
    return _imagen_to_read_with_presigned(img)


@router.delete(
    "/{producto_id}/imagenes/{imagen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_imagen(
    producto_id: int,
    imagen_id: int,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> Response:
    """Soft-delete an image. Reassigns primary if needed."""
    service = ProductService()
    service.delete_imagen(producto_id, imagen_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{producto_id}/imagenes/{imagen_id}/orden",
    response_model=ImagenRead,
)
async def set_imagen_orden(
    producto_id: int,
    imagen_id: int,
    payload: ImagenOrden,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ImagenRead:
    """Update the display order of an image."""
    service = ProductService()
    img = service.set_imagen_orden(producto_id, imagen_id, payload.orden)
    return _imagen_to_read_with_presigned(img)


@router.patch(
    "/{producto_id}/imagenes/{imagen_id}/primaria",
    response_model=ImagenRead,
)
async def set_imagen_primaria(
    producto_id: int,
    imagen_id: int,
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> ImagenRead:
    """Set an image as primary, unsetting all others."""
    service = ProductService()
    img = service.set_imagen_primaria(producto_id, imagen_id)
    return _imagen_to_read_with_presigned(img)
