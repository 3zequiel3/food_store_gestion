# Tasks: product-creation-complete

## Phase 1 — Backend DB & Models (Work Unit: infrastructure)

### Task 1.1 — Alembic migration for product_images table
- Create `alembic/versions/YYYYMMDD_HHMM_create_product_images.py`
- Table: `id, producto_id (FK CASCADE, indexed), url, orden, es_primaria, creado_en, actualizado_en, eliminado_en`
- Backfill: for each product with `imagen_url IS NOT NULL`, insert row with es_primaria=True, orden=0
- `down_revision` points to latest migration
- Run `alembic upgrade head` locally to verify

### Task 1.2 — ProductoImagen model in backend
- Add `ProductoImagen` class in `backend/app/models/producto.py`
- Relationship `producto: Mapped["Producto"] = relationship("Producto", back_populates="imagenes")`
- Add `imagenes: Mapped[List[ProductoImagen]]` to `Producto` model with back_populates
- Add `ImagenRead` schema in `backend/app/schemas/producto.py`
- Update `ProductoRead` to include `imagenes: list[ImagenRead] = []`

### Task 1.3 — Repository methods for ProductoImagen
- Add to `backend/app/repositories/producto.py`:
  - `list_imagenes(producto_id)` — active images ordered by orden
  - `add_imagen(producto_id, url)` — insert row
  - `delete_imagen(imagen_id)` — soft-delete
  - `set_all_non_primaria(producto_id)` — bulk update
  - `set_primaria(imagen_id)` — set flag

## Phase 2 — Backend API Endpoints (Work Unit: image-crud)

### Task 2.1 — POST /{id}/imagenes (file upload)
- New route in `backend/app/routers/productos.py`
- Auth: require_role("ADMIN", "STOCK")
- Multipart file upload → StorageService.save_product_image() → ProductoImagen row
- es_primaria=True if no other images exist for product
- Return 201 with ImagenRead

### Task 2.2 — POST /{id}/imagenes/url
- New route accepting `{"url": str}` (max 500 chars)
- Validate URL format
- Create ProductoImagen row

### Task 2.3 — DELETE /{id}/imagenes/{img_id}
- Soft-delete image row
- If deleted was primary → reassign primary to next image by orden
- Return 204 or 404

### Task 2.4 — PATCH /{id}/imagenes/{img_id}/orden
- Accept `{"orden": int}` and update
- Return 200 with ImagenRead

### Task 2.5 — PATCH /{id}/imagenes/{img_id}/primaria
- Unset es_primaria on all other product images (single UoW transaction)
- Set es_primaria=True on target image
- Return 200 with ImagenRead

### Task 2.6 — Update legacy POST /{id}/imagen to also create ProductoImagen
- Existing endpoint already updates imagen_url field
- Add: also create ProductoImagen row (for backward compat migration path)

## Phase 3 — Backend Schema & Service Changes (Work Unit: validation)

### Task 3.1 — categoria_ids REQUIRED in ProductoCreate
- Change schema: `categoria_ids: list[int]` with `min_length=1`
- Update ProductService.create(): reject empty list with BusinessRuleError "El producto debe tener al menos una categoría"
- Remove the auto-disable hook logic for creation (no longer needed since categorias required)

### Task 3.2 — ingrediente_ids support in ProductoCreate
- Add `ingrediente_ids: list[dict] | None` to ProductoCreate
- Each dict: `{ingrediente_id: int, es_removible: bool}`
- Validate all ingrediente_ids exist (active ingredients)
- On create: associate ingredients within same transaction
- Raise BusinessRuleError if any ingredient doesn't exist (rollback)

### Task 3.3 — Update ProductoRead.imagenes in schema
- Ensure ProductoRead includes `imagenes: list[ImagenRead] = []`
- imagen_url kept as optional for backward compat
- Update ProductoDetail similarly

## Phase 4 — Backend Tests (Work Unit: test-backend)

### Task 4.1 — Test ProductoImagen model and repository
- Unit test: ProductoImagen relationship with Producto
- Unit test: list_imagenes excludes soft-deleted
- Unit test: add_imagen, delete_imagen (soft-delete flag)

### Task 4.2 — Test image CRUD endpoints
- POST /{id}/imagenes: first image is primary, subsequent are not
- POST /{id}/imagenes: rejects non-image file types (422)
- POST /{id}/imagenes/url: valid URL, invalid URL (422)
- DELETE /{id}/imagenes/{img_id}: soft-delete, reassign primary, last image
- PATCH /{id}/imagenes/{img_id}/orden: reorder
- PATCH /{id}/imagenes/{img_id}/primaria: toggle primary

### Task 4.3 — Test categoria_ids required validation
- Missing categoria_ids → 422
- Empty list → 422 BusinessRuleError
- Valid categoria_ids → 201

### Task 4.4 — Test ingrediente_ids on creation
- Create with ingredients → 201 + ingredients associated
- Create with non-existent ingredient → 422 + rollback
- Create without ingredients (backward compat) → 201

## Phase 5 — Frontend Type Fixes (Work Unit: type-fix)

### Task 5.1 — Fix CategoriaRead type
- In `frontend/src/types/products.types.ts`
- Change `parent_id` → `padre_id`
- Remove `slug` field
- Verify all usages of CategoriaRead in CategoryLeafSelector

### Task 5.2 — Add ImagenRead and update ProductoRead
- Add `ImagenRead { id, url, orden, es_primaria }` interface
- Update `ProductoRead` to include `imagenes: ImagenRead[]`
- Keep `imagen_url?: string | null` for backward compat

## Phase 6 — Frontend Service Layer (Work Unit: service-layer)

### Task 6.1 — Admin product image service functions
- In `frontend/src/services/admin/productos.ts`
- Add: `uploadProductImage(id, file)`, `addProductImageUrl(id, url)`, `deleteProductImage(id, imagenId)`, `setProductImagePrimary(id, imagenId)`, `setProductImageOrder(id, imagenId, orden)`

## Phase 7 — Frontend ProductFormModal (Work Unit: form-modal)

### Task 7.1 — Rebuild ProductFormModal with 2-column layout
- Left column: nombre, descripción, precio, stock, disponible, CategoryLeafSelector, IngredientAssignSelector
- Right column: image section with upload/URL toggle, thumbnail list, drag-reorder, set-primary, delete
- Unified create/edit form (same modal for both)
- On submit flow: create product → then upload images → then associate ingredients

### Task 7.2 — Integrate CategoryLeafSelector
- Connect to form with `value` / `onChange`
- Required validation (at least one leaf category)
- Error message when empty on submit

### Task 7.3 — Integrate IngredientAssignSelector
- Connect to form with `value` / `onChange`
- Allow toggle of `es_removible` per ingredient
- Badge for allergens

### Task 7.4 — Image section UI
- Toggle: [📁 Upload] [🔗 URL] buttons
- File mode: drag & drop zone, file input fallback
- URL mode: text input + confirm button
- Thumbnail list: show es_primaria badge (★), drag handle, × delete button
- Click ★ to set as primary
- Visual feedback during upload (loading state)

## Phase 8 — Frontend ProductDetailPage (Work Unit: detail-page)

### Task 8.1 — Image carousel on ProductDetailPage
- Main image area: show primary image (or first by orden if no primary)
- Thumbnail strip below main image
- Click thumbnail → switch main image
- If only 1 image → single image display (no carousel), current behavior preserved
- Skeleton loader for image placeholders

## Phase 9 — Frontend Tests (Work Unit: test-frontend)

### Task 9.1 — Type correctness tests
- CategoriaRead has padre_id, no slug
- ImagenRead has correct shape
- ProductoRead has imagenes array

### Task 9.2 — Component tests
- CategoryLeafSelector integration in form
- IngredientAssignSelector integration in form
- Image upload toggle (file vs URL)
- Thumbnail list (primary badge, delete, reorder)
- ProductFormModal validation (required categories)

### Task 9.3 — Carousel tests on ProductDetailPage
- Single image: no carousel, just image
- Multiple images: carousel with thumbnail strip
- Click thumbnail changes main image

---

## Review Workload Forecast

| Work Unit | Files | Est. Changed Lines |
|---|---|---|
| infrastructure (migration + model) | alembic/versions/*.py, backend/app/models/producto.py | ~120 |
| image-crud (endpoints) | backend/app/routers/productos.py, backend/app/services/producto.py | ~200 |
| validation (schema + service) | backend/app/schemas/producto.py, backend/app/services/producto.py | ~80 |
| test-backend | tests/test_productos.py, tests/test_product_images.py | ~350 |
| type-fix | frontend/src/types/products.types.ts | ~30 |
| service-layer | frontend/src/services/admin/productos.ts | ~80 |
| form-modal (2-col + selectors + images) | frontend/src/components/admin/product/* | ~400 |
| detail-page (carousel) | frontend/src/pages/admin/product/* | ~150 |
| test-frontend | frontend/src/__tests__/components/admin/product/* | ~200 |
| **TOTAL** | | **~1,610 lines** |

## Risks & Skill Resolution

| Risk | Likelihood | Mitigation |
|---|---|---|
| Migration backfill could be slow on large products table | Low | Use batched INSERT with chunking |
| Image upload endpoint needs multipart config in FastAPI | Known | Use `UploadedFile` type from FastAPI, validate MIME types |
| CategoryLeafSelector returns full CategoriaRead[], but backend expects leaf IDs | Known | Ensure selector filters to leaf-only before returning; frontend already has leaf-filter logic |
| Drag-and-drop reorder requires 3rd party lib (dnd-kit or react-beautiful-dnd) | Medium | Use @dnd-kit/core + @dnd-kit/sortable (already in project deps or add) |
| ProductFormModal on EDIT needs to load existing images + categories + ingredients | Known | On edit open: fetch product detail → populate form; separate PUT for basic fields, dedicated endpoints for cats/ings/imgs |
| Legacy `/imagen` endpoint conflict with new `/{id}/imagenes` | Low | Different paths, no conflict |

## Next Recommended
Proceed to `sdd-design` for `products-frontend-complete` change (depends on this change's backend being done first).

## Skill Resolution
- Backend (FastAPI): use context7 for StorageService docs, SQLModel relationship patterns
- Frontend (React): use `frontend-design` for 2-column layout, `vercel-react-best-practices` for component patterns
- Testing: use `go-testing` pattern (pytest fixtures) for backend; vitest for frontend