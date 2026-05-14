# Delta Spec: product-creation-complete → products

## ADDED Requirements

### Requirement: ProductoImagen model for multiple product images
The system SHALL introduce a new `ProductoImagen` model persisted in the `product_images` table with columns: `id BIGSERIAL PRIMARY KEY`, `producto_id INTEGER NOT NULL` (FK to `products.id` with ON DELETE CASCADE, indexed), `url VARCHAR(500) NOT NULL`, `orden INTEGER NOT NULL DEFAULT 0`, `es_primaria BOOLEAN NOT NULL DEFAULT false`, plus standard `creado_en`, `actualizado_en`, `eliminado_en` columns from `BaseModel`. The `Producto` model SHALL have a relationship `imagenes: Mapped[List[ProductoImagen]]` with `back_populates="producto"`. Soft-deleted images (`eliminado_en IS NOT NULL`) SHALL be excluded from all listing and detail responses. (US-015, ERD §3.3)

#### Scenario: ProductoImagen has correct schema
- **WHEN** the `product_images` table is introspected after migration
- **THEN** it has columns `id`, `producto_id`, `url`, `orden`, `es_primaria`, `creado_en`, `actualizado_en`, `eliminado_en`
- **AND** `producto_id` has a foreign key to `products.id` with `ON DELETE CASCADE`
- **AND** `producto_id` is indexed

#### Scenario: Producto model has imagenes relationship
- **WHEN** the `Producto` class is introspected
- **THEN** it has an attribute `imagenes` that is a `relationship` to `ProductoImagen`

#### Scenario: Soft-deleted images are excluded
- **GIVEN** product 5 has 3 images, one with `eliminado_en` set
- **WHEN** `list_imagenes(5)` is called
- **THEN** the result contains only 2 images

### Requirement: Alembic migration creates product_images and backfills
The system SHALL include an Alembic migration that: (1) creates the `product_images` table, (2) backfills existing `imagen_url` values by inserting a `ProductoImagen` row for each product where `imagen_url IS NOT NULL` and `eliminado_en IS NULL`, with `es_primaria=true`, `orden=0`. The migration `down_revision` SHALL point to the latest existing migration. (ERD §3.3)

#### Scenario: Migration creates table and backfills
- **WHEN** `alembic upgrade head` is executed
- **THEN** the `product_images` table exists
- **AND** every product with a non-null `imagen_url` has a corresponding row in `product_images` with `es_primaria=true`

#### Scenario: Downgrade drops table
- **WHEN** `alembic downgrade -1` is executed
- **THEN** the `product_images` table no longer exists

### Requirement: categoria_ids is REQUIRED in ProductoCreate
The `ProductoCreate` schema SHALL require `categoria_ids: list[int]` with `min_length=1` (at least one leaf category). The value SHALL NOT be `None` and SHALL NOT be an empty list. If `categoria_ids` is missing, `None`, or empty, the service SHALL raise `BusinessRuleError` with the message "El producto debe tener al menos una categoría". This replaces the previous behavior where `categoria_ids` was optional (`None` meant "skip category association"). (US-015, RN-CA06)

#### Scenario: categoria_ids missing rejected
- **WHEN** a POST payload omits `categoria_ids` entirely
- **THEN** the response is 422 (Pydantic validation error — required field)

#### Scenario: categoria_ids empty list rejected
- **WHEN** a POST payload has `categoria_ids: []`
- **THEN** the response is 422 (`BusinessRuleError`) with message referencing "al menos una categoría"

#### Scenario: categoria_ids with valid leaf categories accepted
- **GIVEN** leaf categories 6 and 7 exist
- **WHEN** POST with `{"nombre": "X", "precio": 10, "categoria_ids": [6, 7]}`
- **THEN** the response is 201 AND product is associated with both categories

### Requirement: Ingredient assignment on product creation
The `ProductoCreate` schema SHALL accept an optional `ingrediente_ids: list[dict] | None` field where each dict contains `ingrediente_id: int` and `es_removible: bool`. When provided, the service SHALL associate each ingredient with the newly created product within the same transaction. Each `ingrediente_id` SHALL be validated to exist as an active ingredient. If any ingredient does not exist, the service SHALL raise `BusinessRuleError` and the entire creation SHALL be rolled back. (US-015, US-017)

#### Scenario: Create product with ingredients
- **GIVEN** active ingredients 10 and 11 exist
- **WHEN** POST with `{"nombre": "X", "precio": 10, "categoria_ids": [6], "ingrediente_ids": [{"ingrediente_id": 10, "es_removible": true}, {"ingrediente_id": 11, "es_removible": false}]}`
- **THEN** the response is 201 AND `GET /{id}/ingredientes` returns both ingredients with correct `es_removible` flags

#### Scenario: Non-existent ingredient_id rejected
- **GIVEN** ingredient 99999 does not exist
- **WHEN** POST with `{"nombre": "X", "precio": 10, "categoria_ids": [6], "ingrediente_ids": [{"ingrediente_id": 99999, "es_removible": true}]}`
- **THEN** the response is 422 (`BusinessRuleError`) AND no product is created (rolled back)

#### Scenario: Create product without ingredients (backward compat)
- **WHEN** POST with `{"nombre": "X", "precio": 10, "categoria_ids": [6]}` (no `ingrediente_ids`)
- **THEN** the response is 201 AND product has no ingredients

### Requirement: ImagenRead output schema
The system SHALL provide an `ImagenRead` Pydantic schema with fields: `id: int`, `url: str`, `orden: int`, `es_primaria: bool`. This schema SHALL be used in `ProductoRead.imagenes` and in image CRUD endpoint responses.

#### Scenario: ImagenRead serializes correctly
- **WHEN** a `ProductoImagen` row is validated through `ImagenRead`
- **THEN** the output contains `id`, `url`, `orden`, `es_primaria`

### Requirement: ProductoRead includes imagenes list
The `ProductoRead` schema SHALL include `imagenes: list[ImagenRead] = []`. The `imagen_url` field SHALL be preserved for backward compatibility during the transition period. When serializing from a `Producto` model, `imagenes` SHALL be populated from the `producto.imagenes` relationship (filtered to active rows only). (US-019)

#### Scenario: ProductoRead has imagenes list
- **WHEN** `GET /api/v1/productos` is called
- **THEN** each item in `items` has an `imagenes` array (may be empty)

#### Scenario: imagen_url preserved for backward compat
- **WHEN** `GET /api/v1/productos` is called
- **THEN** each item still has `imagen_url` (may be null)

### Requirement: Product detail includes imagenes
The `ProductoDetail` schema SHALL include `imagenes: list[ImagenRead]` in addition to `categorias` and `ingredientes`. The images SHALL be ordered by `orden` ascending, then by `id` ascending. (US-019)

#### Scenario: Detail returns ordered images
- **GIVEN** product 5 has images with orden [2, 0, 1]
- **WHEN** `GET /api/v1/productos/5` is called
- **THEN** `imagenes` is ordered [0, 1, 2] by orden

### Requirement: Upload image endpoint (file)
The system SHALL expose `POST /api/v1/productos/{id}/imagenes` protected by `require_role("ADMIN", "STOCK")` that accepts a multipart file upload. The service SHALL: (1) validate the product exists, (2) call `StorageService.save_product_image()` to save the file, (3) create a `ProductoImagen` row with `orden = max_existing_orden + 1` and `es_primaria = True` if no other primary image exists for this product, (4) return 201 with `ImagenRead`. (US-015)

#### Scenario: Upload image as first image
- **GIVEN** product 5 has no images
- **WHEN** POST `/api/v1/productos/5/imagenes` with a valid image file
- **THEN** the response is 201 with `es_primaria: true`, `orden: 0`

#### Scenario: Upload image when primary already exists
- **GIVEN** product 5 already has a primary image
- **WHEN** POST with another valid image file
- **THEN** the response is 201 with `es_primaria: false`, `orden: 1`

#### Scenario: Upload invalid file type rejected
- **WHEN** POST with a PDF file
- **THEN** the response is 422 (`BusinessRuleError`) with message about valid image types

### Requirement: Add image by URL endpoint
The system SHALL expose `POST /api/v1/productos/{id}/imagenes/url` protected by `require_role("ADMIN", "STOCK")` that accepts `{"url": str}` (max 500 chars). The service SHALL validate the URL format, create a `ProductoImagen` row with the URL, and return 201 with `ImagenRead`. (US-015)

#### Scenario: Add image by URL
- **WHEN** POST `/api/v1/productos/5/imagenes/url` with `{"url": "https://example.com/img.jpg"}`
- **THEN** the response is 201 with the provided URL

#### Scenario: Invalid URL rejected
- **WHEN** POST with `{"url": "not-a-url"}`
- **THEN** the response is 422

### Requirement: Delete image endpoint
The system SHALL expose `DELETE /api/v1/productos/{id}/imagenes/{img_id}` protected by `require_role("ADMIN", "STOCK")` that soft-deletes the image row. If the deleted image was primary, the service SHALL set the next image (by orden) as primary. Returns 204 on success, 404 if not found or already deleted. (US-015)

#### Scenario: Delete non-primary image
- **GIVEN** product 5 has images [primary, non-primary]
- **WHEN** DELETE the non-primary image
- **THEN** the response is 204 AND the primary image remains primary

#### Scenario: Delete primary image reassigns
- **GIVEN** product 5 has images [primary(A), secondary(B)]
- **WHEN** DELETE image A (primary)
- **THEN** the response is 204 AND image B becomes primary

#### Scenario: Delete last image
- **GIVEN** product 5 has only one image
- **WHEN** DELETE that image
- **THEN** the response is 204 AND product has no images

### Requirement: Set image order endpoint
The system SHALL expose `PATCH /api/v1/productos/{id}/imagenes/{img_id}/orden` protected by `require_role("ADMIN", "STOCK")` that accepts `{"orden": int}`. The service SHALL update the image's `orden` value. Returns 200 with `ImagenRead`. (US-015)

#### Scenario: Change image order
- **WHEN** PATCH with `{"orden": 5}`
- **THEN** the response is 200 with `orden: 5`

### Requirement: Set primary image endpoint
The system SHALL expose `PATCH /api/v1/productos/{id}/imagenes/{img_id}/primaria` protected by `require_role("ADMIN", "STOCK")`. The service SHALL set `es_primaria = True` on the target image and `es_primaria = False` on all other images for the same product, within a single transaction. Returns 200 with `ImagenRead`. (US-015)

#### Scenario: Set new primary image
- **GIVEN** product 5 has images [A(primary), B, C]
- **WHEN** PATCH `/api/v1/productos/5/imagenes/B/primaria`
- **THEN** the response is 200 AND image B has `es_primaria: true` AND image A has `es_primaria: false`

### Requirement: Existing single-image upload creates ProductoImagen
The existing `POST /api/v1/productos/{id}/imagen` endpoint SHALL be updated to ALSO create a `ProductoImagen` row in addition to updating the product's `imagen_url` field. This ensures backward compatibility while populating the new table. If the product already has images, the new row is added with `orden = max + 1`. If no images exist, it is created as primary. (US-015)

#### Scenario: Legacy upload creates ProductoImagen row
- **GIVEN** product 5 has no images
- **WHEN** POST `/api/v1/productos/5/imagen` with a file (legacy endpoint)
- **THEN** the product's `imagen_url` is updated AND a `ProductoImagen` row is created with `es_primaria: true`

## MODIFIED Requirements

### Requirement: Create product endpoint (MODIFIED)
**CHANGE**: `categoria_ids` is now REQUIRED (was optional). The schema field changes from `categoria_ids: list[int] | None = None` to `categoria_ids: list[int]` with `min_length=1`. The service no longer accepts `None` or empty list — both raise `BusinessRuleError`. The auto-disable hook is no longer needed for creation (since categories are required), but the validation logic remains for `set_categorias`.

**CHANGE**: `ProductoCreate` now accepts `ingrediente_ids: list[dict] | None` for assigning ingredients at creation time.

(Previously: `categoria_ids` was optional with `None` default; no ingredient assignment on create)

#### Scenario: Successful product creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Hamburguesa Clásica", "precio": 12.50, "stock_cantidad": 30, "categoria_ids": [6]}`
- **THEN** the response is 201 with body containing `id`, `nombre`, `precio`, `stock_cantidad`, `disponible: true`

#### Scenario: Successful product creation as STOCK with leaf categorias
- **GIVEN** active leaf categories with ids 1 and 2 exist
- **WHEN** a user with role `STOCK` posts `{"nombre": "Pizza", "precio": 18.00, "categoria_ids": [1, 2]}`
- **THEN** the response is 201 AND rows exist in `product_categories` AND `disponible: true`

#### Scenario: Empty categoria_ids list rejected
- **WHEN** a payload with `categoria_ids: []` is posted
- **THEN** the response is 422 (`BusinessRuleError`) with message referencing "al menos una categoría"

#### Scenario: categoria_ids missing rejected
- **WHEN** a payload omits the `categoria_ids` key entirely
- **THEN** the response is 422 (Pydantic validation — required field)

### Requirement: Get product detail endpoint (MODIFIED)
**CHANGE**: `ProductoDetail` now includes `imagenes: list[ImagenRead]` ordered by `orden` ascending, then `id` ascending.

(Previously: returned only `categorias` and `ingredientes`, no `imagenes`)

#### Scenario: Returns full detail with associations and images
- **GIVEN** product P with categories [1,2], ingredients [10,11], images [A(primary), B]
- **WHEN** `GET /api/v1/productos/{P.id}` is called
- **THEN** the response includes `categorias`, `ingredientes`, AND `imagenes` with correct ordering

### Requirement: Update product endpoint (MODIFIED)
**CHANGE**: `ProductoRead` response now includes `imagenes` list.

(Previously: response had `imagen_url` only, no `imagenes` array)

#### Scenario: Successful update returns imagenes
- **WHEN** PUT `/api/v1/productos/5` with `{"nombre": "Nuevo nombre"}`
- **THEN** the response is 200 with `imagenes` array (may be empty)
