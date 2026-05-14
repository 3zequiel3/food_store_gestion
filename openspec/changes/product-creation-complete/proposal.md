# Change: product-creation-complete

## Why

The current product creation flow is incomplete and unsafe:

1. **Products can be created without categories** — the backend allows `categoria_ids: None` (skipping validation) and the frontend form has no category selector at all. This violates the business rule that every product must belong to at least one leaf category.
2. **No ingredient assignment during creation** — ingredients must be added via a separate endpoint after the product exists, creating a multi-step workflow that is error-prone.
3. **Single image per product** — the `products` table has only one `imagen_url` column. There is no `ProductoImagen` model, no image upload endpoint, no carousel on the detail page.
4. **Orphaned UI components** — `CategoryLeafSelector` and `IngredientAssignSelector` exist in the frontend but have zero imports. They were built for this exact purpose but never connected.
5. **Category type mismatch** — frontend `CategoriaRead` in `products.types.ts` has `slug` + `parent_id`, but the backend sends `padre_id` without `slug`. This causes runtime type errors.

This change closes all gaps: unified product form (create = edit) with categories + ingredients + images in a single flow, backend multi-image support, and type alignment.

## What changes

### Backend
- New `ProductoImagen` model + Alembic migration (id, producto_id FK, url, orden, es_primaria, created_at)
- `ProductoCreate.categoria_ids` becomes **required** (at least 1 leaf category)
- `ProductoRead` returns `imagenes: list[ImagenRead]` instead of single `imagen_url`
- New image CRUD endpoints: upload, delete, reorder, set primary
- `POST /productos` accepts `ingrediente_ids: list[{id, es_removible}]` alongside `categoria_ids`
- Existing single-image upload endpoint (`POST /{id}/imagen`) deprecated in favor of multi-image endpoints

### Frontend
- `ProductFormModal` rebuilt with 2-column layout: left = data fields + category selector + ingredient selector, right = image section (file upload toggle vs URL input)
- Connect orphaned `CategoryLeafSelector` and `IngredientAssignSelector` into the modal
- `ProductDetailPage` gets image carousel with thumbnails
- Fix `CategoriaRead` type: use `padre_id` (not `parent_id`), remove `slug`

### What stays the same
- `shared/storage.py` is reused as-is (already handles local + S3)
- `CategoryLeafSelector` and `IngredientAssignSelector` are connected, not rewritten
- Existing product CRUD endpoints remain (backward compatible where possible)
- Soft-delete patterns, UoW, repository layer — unchanged

## Impact

- **Affected specs**: `products`, `admin-products`
- **Affected modules**: `backend/features/products/{models,schemas,router,service,repository}.py`, new migration
- **Affected frontend**: `ProductFormModal`, `ProductDetailPage`, `products.types.ts`, admin-products service
- **Breaking**: `ProductoRead` shape changes (`imagen_url` → `imagenes` list). Frontend `CategoriaRead` type corrected.
- **Migration**: Alembic migration creates `product_images` table, backfills existing `imagen_url` values as primary images

## Risks

| Risk | Mitigation |
|------|-----------|
| Breaking `imagen_url` → `imagenes` for existing consumers | Backfill migration ensures every product with an existing `imagen_url` gets a `ProductoImagen` row. Frontend reads `imagenes[0]` as fallback for single-image cases. |
| `categoria_ids` required breaks existing API callers | This is an admin-only endpoint. The frontend is updated in the same change. No external consumers exist. |
| Image upload size/performance | `shared/storage.py` already validates max size. Multi-image upload is sequential (not parallel) to avoid overwhelming the server. |
| Migration backfill on large datasets | Backfill runs in a single transaction. For production with many products, we'd chunk it, but current dataset is small (seed data only). |

## Non-goals

- Bulk image upload (drag multiple files at once) — out of scope
- Image cropping/editing — out of scope
- CDN integration beyond existing S3 proxy — out of scope
- Product import/export (CSV) — out of scope
