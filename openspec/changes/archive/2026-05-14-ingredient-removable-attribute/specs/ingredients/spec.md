# Delta for ingredients

## MODIFIED Requirements

### Requirement: Ingrediente entity model

The system SHALL persist ingredients in the existing `ingredients` table with columns `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL UNIQUE`, `es_alergeno BOOLEAN NOT NULL DEFAULT false`, `es_removible BOOLEAN NOT NULL DEFAULT false`, plus standard `creado_en/actualizado_en/eliminado_en TIMESTAMPTZ` from `BaseModel`. The ORM class `Ingrediente` defined in `backend/features/catalog/models.py` SHALL be the single source of truth. (Previously: `es_removible` was NOT on this model — it lived on `ProductoIngrediente` pivot)

#### Scenario: Ingrediente has es_removible boolean column

- **WHEN** the `ingredients` table schema is introspected
- **THEN** column `es_removible` exists as `BOOLEAN NOT NULL DEFAULT false`

#### Scenario: Ingrediente has UNIQUE constraint on nombre

- **WHEN** the `ingredients` table schema is introspected
- **THEN** there exists a UNIQUE constraint named `uq_ingredients_nombre` on column `nombre`

#### Scenario: Ingrediente has es_alergeno boolean column

- **WHEN** the `ingredients` table schema is introspected
- **THEN** column `es_alergeno` exists as `BOOLEAN NOT NULL DEFAULT false`

#### Scenario: Ingrediente ORM is reused, not redefined

- **WHEN** `backend.features.ingredients.repository` is imported
- **THEN** it imports `Ingrediente` from `backend.features.catalog.models` and does NOT declare a new SQLAlchemy class

#### Scenario: Ingrediente inherits soft-delete from BaseModel

- **WHEN** an `Ingrediente` instance is loaded from the database
- **THEN** it exposes `id`, `nombre`, `es_alergeno`, `es_removible`, `creado_en`, `actualizado_en`, `eliminado_en`

### Requirement: Create ingredient endpoint

The system SHALL expose `POST /api/v1/ingredientes` protected by `require_role("ADMIN", "STOCK")` that accepts `IngredienteCreate({nombre: str, es_alergeno: bool = False, es_removible: bool = False})`. On success it SHALL return 201 with `IngredienteRead`. (Previously: `IngredienteCreate` did NOT include `es_removible`)

#### Scenario: Successful ingredient creation with es_removible

- **WHEN** a user with role `ADMIN` posts `{"nombre": "Tomate", "es_removible": true}`
- **THEN** the response is 201 with `es_removible: true`

#### Scenario: es_removible defaults to false when omitted

- **WHEN** a user with role `ADMIN` posts `{"nombre": "Lechuga"}`
- **THEN** the response is 201 with `es_removible: false`

#### Scenario: Successful ingredient creation as ADMIN

- **WHEN** a user with role `ADMIN` posts `{"nombre": "Tomate", "es_alergeno": false}`
- **THEN** the response is 201 with body containing `id`, `nombre`, `es_alergeno`, `es_removible`, `creado_en`, `actualizado_en`

#### Scenario: Unauthenticated request rejected

- **WHEN** an anonymous client posts to `/api/v1/ingredientes`
- **THEN** the response is 401 (RFC 7807)

#### Scenario: CLIENT role forbidden

- **WHEN** a user with role `CLIENT` posts a valid create payload
- **THEN** the response is 403 (RFC 7807)

### Requirement: List ingredients endpoint with pagination and filter

The system SHALL expose `GET /api/v1/ingredientes` (public) returning `PaginatedIngredientes({items: list[IngredienteRead], total, page, limit})`. Accepts query params `page`, `limit`, `es_alergeno: bool | None`, and `es_removible: bool | None`. When `es_removible` is provided, filters by that value. Soft-deleted ingredients excluded. (Previously: no `es_removible` filter param)

#### Scenario: Filter es_removible=true returns only removable ingredients

- **GIVEN** 3 ingredients with `es_removible=true` and 7 with `es_removible=false`
- **WHEN** `GET /api/v1/ingredientes?es_removible=true` is called
- **THEN** the response is 200 with `items.length == 3`, every item has `es_removible: true`

#### Scenario: Filter es_removible=false returns only non-removable

- **GIVEN** 3 ingredients with `es_removible=true` and 7 with `es_removible=false`
- **WHEN** `GET /api/v1/ingredientes?es_removible=false` is called
- **THEN** the response is 200 with `items.length == 7`

#### Scenario: Default pagination returns first 20 items

- **GIVEN** 25 non-deleted ingredients exist
- **WHEN** `GET /api/v1/ingredientes` is called
- **THEN** the response is 200 with `items.length == 20`, `total == 25`, `page == 1`, `limit == 20`

#### Scenario: Endpoint is public

- **WHEN** an anonymous client calls `GET /api/v1/ingredientes`
- **THEN** the response is 200

### Requirement: Update ingredient endpoint

The system SHALL expose `PUT /api/v1/ingredientes/{id}` protected by `require_role("ADMIN", "STOCK")` that accepts `IngredienteUpdate({nombre: str | None, es_alergeno: bool | None, es_removible: bool | None})`. Uses `model_dump(exclude_unset=True)`. (Previously: `IngredienteUpdate` did NOT include `es_removible`)

#### Scenario: Successful es_removible-only update

- **GIVEN** ingredient `id=5, es_removible=false`
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"es_removible": true}`
- **THEN** the response is 200 with `es_removible: true`, other fields preserved

#### Scenario: Successful nombre-only update preserves es_removible

- **GIVEN** ingredient `id=5, nombre="Tomate", es_removible=true`
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"nombre": "Tomate Cherry"}`
- **THEN** the response is 200 with `nombre: "Tomate Cherry", es_removible: true`

#### Scenario: Non-existent ingredient returns 404

- **WHEN** PUT `/api/v1/ingredientes/99999` with any payload
- **THEN** the response is 404

## REMOVED Requirements

### Requirement: API versioned prefix and Spanish naming

(Reason: Unchanged — no modification needed. This requirement remains as-is in the main spec.)
