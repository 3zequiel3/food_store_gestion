# Design: product-creation-complete

## Architecture

This change touches both backend and frontend in a coordinated way. The backend provides the data model and API; the frontend consumes it in a unified admin form.

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript)                              │
│  ProductFormModal (2-column layout)                         │
│  ├─ Left: nombre, descripción, precio, stock, disponible    │
│  │       + CategoryLeafSelector + IngredientAssignSelector  │
│  └─ Right: Image section (upload toggle / URL input)        │
│       + thumbnail list + drag-reorder + set-primary         │
├─────────────────────────────────────────────────────────────┤
│  API Contract (FastAPI)                                     │
│  POST   /api/v1/productos              (create + cats + ings)│
│  PUT    /api/v1/productos/{id}         (update basic fields) │
│  POST   /api/v1/productos/{id}/imagenes (upload new image)  │
│  DELETE /api/v1/productos/{id}/imagenes/{img_id}            │
│  PATCH  /api/v1/productos/{id}/imagenes/{img_id}/orden      │
│  PATCH  /api/v1/productos/{id}/imagenes/{img_id}/primaria   │
│  GET    /api/v1/productos/{id}          (detail + imagenes)  │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLModel)                               │
│  Router → Service → UoW → Repo → Model                      │
│  ProductoImagen model + product_images table                │
│  StorageService reused (local/S3)                           │
└─────────────────────────────────────────────────────────────┘
```

## Backend Design

### D1. New `ProductoImagen` Model

```python
class ProductoImagen(BaseModel):
    __tablename__ = "product_images"

    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    es_primaria: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    producto: Mapped["Producto"] = relationship("Producto", back_populates="imagenes")
```

**Design decisions:**
- Surrogate `id` from `BaseModel` (standard pattern)
- `producto_id` indexed for fast lookup by product
- `orden` controls display order (0-based, lower = first)
- `es_primaria` flag for the "hero" image (only one per product, enforced in service)
- CASCADE on delete: if product is hard-deleted, images go too (soft-delete of product doesn't cascade — images stay)

### D2. Migration Strategy

New Alembic migration after `20260512_1308` (`0b02f52c7d8a_add_motivo_to_order_state_history`):

1. Create `product_images` table
2. Backfill: for every product with `imagen_url IS NOT NULL`, insert a `ProductoImagen` row with `es_primaria=True`, `orden=0`, `url = imagen_url`
3. Do NOT drop `imagen_url` column yet (kept for backward compatibility during transition)

```python
def upgrade() -> None:
    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("es_primaria", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill existing imagen_url values
    op.execute("""
        INSERT INTO product_images (producto_id, url, orden, es_primaria, creado_en, actualizado_en)
        SELECT id, imagen_url, 0, true, NOW(), NOW()
        FROM products
        WHERE imagen_url IS NOT NULL AND eliminado_en IS NULL
    """)
```

### D3. Schema Changes

```python
class ImagenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    orden: int
    es_primaria: bool

class ProductoRead(BaseModel):
    # ... existing fields ...
    imagenes: list[ImagenRead] = []  # replaces imagen_url

class ProductoCreate(BaseModel):
    # ... existing fields ...
    categoria_ids: list[int] = Field(..., min_length=1)  # NOW REQUIRED
    ingrediente_ids: list[dict] | None = None  # NEW: [{ingrediente_id, es_removible}]

class ProductoUpdate(BaseModel):
    # unchanged — categoria_ids and ingredientes managed via dedicated endpoints
```

### D4. New Image Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/{id}/imagenes` | ADMIN/STOCK | Upload new image via multipart file |
| POST | `/{id}/imagenes/url` | ADMIN/STOCK | Add image via URL string |
| DELETE | `/{id}/imagenes/{img_id}` | ADMIN/STOCK | Soft-delete an image |
| PATCH | `/{id}/imagenes/{img_id}/orden` | ADMIN/STOCK | Change display order |
| PATCH | `/{id}/imagenes/{img_id}/primaria` | ADMIN/STOCK | Set as primary image |

**Upload flow:**
1. Validate product exists
2. Call `StorageService.save_product_image(producto_id, file)` → returns URL
3. Create `ProductoImagen` row with `orden = max(existing) + 1`, `es_primaria = True` if no other primary exists
4. Return `ImagenRead`

**Set primary flow:**
1. Set `es_primaria = False` on all other images for this product
2. Set `es_primaria = True` on target image
3. All within same UoW transaction

### D5. Service Changes

**`ProductService.create()` modifications:**
- `categoria_ids` is now required (not None). If empty list → BusinessRuleError.
- After creating product, associate ingredients if `ingrediente_ids` provided.
- The auto-disable hook still runs (but won't trigger since categorias are required).

**New service methods:**
- `add_imagen(producto_id, file)` → upload + save
- `add_imagen_from_url(producto_id, url)` → validate URL + save
- `delete_imagen(producto_id, imagen_id)` → soft-delete pivot
- `set_imagen_orden(producto_id, imagen_id, new_orden)` → reorder
- `set_imagen_primaria(producto_id, imagen_id)` → set primary (unsets others)

### D6. Repository Changes

New methods on `ProductRepository`:
- `list_imagenes(producto_id)` → active images ordered by `orden`
- `add_imagen(producto_id, url)` → insert row
- `delete_imagen(imagen_id)` → soft-delete
- `set_all_non_primaria(producto_id)` → bulk update
- `set_primaria(imagen_id)` → set flag

### D7. Backward Compatibility

The existing `POST /{id}/imagen` endpoint is preserved but now also creates a `ProductoImagen` row in addition to updating `imagen_url`. This ensures that any existing callers (Postman scripts, etc.) continue to work.

The `GET /{id}` detail endpoint now returns `imagenes` in addition to `categorias` and `ingredientes`. The `imagen_url` field is kept on `ProductoRead` for backward compat during transition.

## Frontend Design

### D8. ProductFormModal — 2-Column Layout

```
┌──────────────────────────────────────────────────────────┐
│  [×] Nuevo producto / Editar producto                    │
├──────────────────────────┬───────────────────────────────┤
│  LEFT COLUMN (data)      │  RIGHT COLUMN (images)        │
│                          │                               │
│  Nombre *                │  ┌─────────────────────────┐  │
│  Descripción             │  │  [📁 Upload]  [🔗 URL]  │  │
│  Precio *   Stock        │  └─────────────────────────┘  │
│  Disponible ☑             │                               │
│                          │  ┌─ Thumbnail list ─────────┐  │
│  ── Categorías ──        │  │ [🖼] [🖼] [🖼] [+]       │  │
│  [CategoryLeafSelector]  │  │  ★    ·    ·    +Add     │  │
│                          │  └──────────────────────────┘  │
│  ── Ingredientes ──      │                               │
│  [IngredientAssignSelector]│  Drag to reorder             │
│                          │  Click ★ to set primary        │
│                          │  Click × to delete             │
├──────────────────────────┴───────────────────────────────┤
│  [Cancelar]                    [Guardar producto]         │
└──────────────────────────────────────────────────────────┘
```

**Key behaviors:**
- Create and Edit use the SAME modal (unified)
- Categories: `CategoryLeafSelector` connected with `value`/`onChange`
- Ingredients: `IngredientAssignSelector` connected with `value`/`onChange`
- Image section: toggle between file upload (drag & drop) and URL input
- Thumbnails show primary badge (★), drag handles for reorder, × for delete
- On submit: create product → then upload images → then associate ingredients (sequential)

### D9. Type Fixes

**`CategoriaRead` in `products.types.ts`:**
```typescript
// BEFORE (wrong)
export interface CategoriaRead {
  id: number;
  nombre: string;
  slug: string;          // ← doesn't exist in backend
  parent_id: number | null;  // ← backend sends padre_id
}

// AFTER (correct — matches backend CategoriaRead)
export interface CategoriaRead {
  id: number;
  nombre: string;
  padre_id: number | null;
}
```

**`ProductoRead` in `products.types.ts`:**
```typescript
// Add imagen type
export interface ImagenRead {
  id: number;
  url: string;
  orden: number;
  es_primaria: boolean;
}

// Update ProductoRead
export interface ProductoRead {
  // ... existing fields ...
  imagenes: ImagenRead[];  // replaces imagen_url
  imagen_url?: string | null;  // kept for backward compat
}
```

### D10. ProductDetailPage — Image Carousel

Replace the single `ProductImage` with a carousel:
- Main image area shows the primary image (or first image if no primary)
- Thumbnail strip below main image
- Click thumbnail to switch main image
- If only 1 image → no carousel, just the single image (current behavior preserved)
- Skeleton loader shows placeholder for all expected images

### D11. Image Upload Service

New admin service functions:
```typescript
export async function uploadProductImage(id: number, file: File): Promise<ImagenRead>
export async function addProductImageUrl(id: number, url: string): Promise<ImagenRead>
export async function deleteProductImage(id: number, imagenId: number): Promise<void>
export async function setProductImagePrimary(id: number, imagenId: number): Promise<void>
export async function setProductImageOrder(id: number, imagenId: number, orden: number): Promise<void>
```

## Testing Strategy

- **Backend**: pytest tests for new model, migration, image CRUD endpoints, required categoria_ids validation, ingredient assignment on create
- **Frontend**: vitest tests for type correctness, component rendering of selectors, carousel behavior
- **Integration**: E2E test for full product creation flow (categories + ingredients + image)

## Dependencies

- Depends on: `products-backend` ✅ (archived), `categories-backend` ✅ (archived), `ingredients-backend` ✅ (archived)
- `shared/storage.py` already exists and is reused
- `CategoryLeafSelector` and `IngredientAssignSelector` already exist
