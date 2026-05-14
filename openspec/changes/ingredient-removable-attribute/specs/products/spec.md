# Delta for products

## MODIFIED Requirements

### Requirement: ProductoIngrediente pivot has es_removible flag

The system SHALL remove the `es_removible` column from the `product_ingredients` pivot table via an Alembic migration. The `es_removible` attribute moves to the `Ingrediente` model (see `ingredients` delta spec). The `ProductoIngrediente` ORM class SHALL no longer declare `es_removible`. (Previously: `es_removible` was a column on `product_ingredients` with `BOOLEAN NOT NULL DEFAULT false`)

#### Scenario: Migration removes es_removible from product_ingredients

- **WHEN** `alembic upgrade head` is executed
- **THEN** the `product_ingredients` table no longer contains the column `es_removible`

#### Scenario: Migration adds es_removible to ingredients (cross-ref)

- **WHEN** `alembic upgrade head` is executed
- **THEN** the `ingredients` table contains `es_removible BOOLEAN NOT NULL DEFAULT false`

#### Scenario: ORM model no longer declares es_removible

- **WHEN** the class `ProductoIngrediente` is introspected
- **THEN** it does NOT have an attribute `es_removible`

### Requirement: List products endpoint with combined filters

The system SHALL expose `GET /api/v1/productos` (public) with filters including `excluir_alergenos` and `excluir_alergeno_ids`. The allergen exclusion logic SHALL source `es_removible` from `Ingrediente.es_removible` (joined via `product_ingredients.ingredient_id`) instead of from the pivot row. (Previously: the subqueries joined `product_ingredients.es_removible` directly)

#### Scenario: excluir_alergenos hides products with non-removable allergens

- **GIVEN** product P1 has ingredient I (es_alergeno=true, es_removible=false on Ingrediente); product P2 has ingredient I (es_removible=true on Ingrediente); product P3 has no allergens
- **WHEN** `GET /api/v1/productos?excluir_alergenos=true` is called
- **THEN** the response includes P2 and P3, excludes P1

#### Scenario: excluir_alergeno_ids uses Ingrediente.es_removible

- **GIVEN** ingredient id 50 has `es_removible=false` on `Ingrediente`; product P1 has ingredient 50; product P2 has ingredient 50 but ingredient has `es_removible=true`
- **WHEN** `GET /api/v1/productos?excluir_alergeno_ids=50` is called
- **THEN** P1 is excluded, P2 is included (filter reads from `Ingrediente.es_removible`)

#### Scenario: Default list excludes unavailable

- **GIVEN** 3 products with `disponible=true` and 2 with `disponible=false`
- **WHEN** `GET /api/v1/productos` is called
- **THEN** the response has `total: 3`

#### Scenario: Combined filters AND together

- **WHEN** `GET /api/v1/productos?categoria_id=1&excluir_alergeno_ids=50&disponible=true` is called
- **THEN** only products passing all filters are returned

### Requirement: Get product detail endpoint

The system SHALL expose `GET /api/v1/productos/{id}` (public) returning `ProductoDetail` with `ingredientes: list[IngredienteAsociadoRead]`. Each ingredient's `es_removible` SHALL be sourced from `Ingrediente.es_removible` (not from the pivot). The `IngredienteAsociadoRead` DTO shape stays the same. (Previously: `es_removible` was read from `ProductoIngrediente.es_removible`)

#### Scenario: Returns full detail with es_removible from Ingrediente

- **GIVEN** product P with ingredient 10 (Ingrediente.es_removible=true) and ingredient 11 (Ingrediente.es_removible=false)
- **WHEN** `GET /api/v1/productos/{id}` is called
- **THEN** `ingredientes` contains entries with `es_removible` matching the `Ingrediente` values

#### Scenario: DTO shape unchanged

- **WHEN** the response is deserialized
- **THEN** each item in `ingredientes` has `id`, `nombre`, `es_alergeno`, `es_removible`

### Requirement: Add ingrediente association endpoint

The system SHALL expose `POST /api/v1/productos/{id}/ingredientes` protected by `require_role("ADMIN", "STOCK")` that accepts `AsociarIngrediente({ingrediente_id: int})` (WITHOUT `es_removible`). The pivot row stores only the FK relationship. (Previously: `AsociarIngrediente` included `es_removible: bool = False`)

#### Scenario: Successful association without es_removible

- **GIVEN** product 5 active and ingredient 10 active
- **WHEN** POST `/api/v1/productos/5/ingredientes` with `{"ingrediente_id": 10}`
- **THEN** the response is 201 with `IngredienteAsociadoRead` where `es_removible` comes from `Ingrediente.es_removible`

#### Scenario: Duplicate active association rejected

- **GIVEN** an active pivot row exists for (product 5, ingredient 10)
- **WHEN** POST with `{"ingrediente_id": 10}`
- **THEN** the response is 409

#### Scenario: Soft-deleted association is reactivated

- **GIVEN** a soft-deleted pivot row exists for (product 5, ingredient 10)
- **WHEN** POST with `{"ingrediente_id": 10}`
- **THEN** the response is 201, pivot row reactivated (no `es_removible` on pivot)

#### Scenario: Non-existent ingrediente_id returns 422

- **WHEN** POST with `{"ingrediente_id": 99999}`
- **THEN** the response is 422

### Requirement: List ingredientes of product endpoint

The system SHALL expose `GET /api/v1/productos/{id}/ingredientes` (public) returning `list[IngredienteAsociadoRead]` where `es_removible` is sourced from `Ingrediente.es_removible`. (Previously: `es_removible` came from the pivot row)

#### Scenario: Returns associated ingredients with es_removible from Ingrediente

- **GIVEN** product 5 has ingredients [10 (Ingrediente.es_removible=true), 11 (Ingrediente.es_removible=false)]
- **WHEN** `GET /api/v1/productos/5/ingredientes` is called
- **THEN** the response has `[{id:10, es_removible:true}, {id:11, es_removible:false}]`

#### Scenario: Soft-deleted association excluded

- **GIVEN** pivot row for ingredient 11 has `eliminado_en` set
- **WHEN** the endpoint is called
- **THEN** only ingredient 10 is returned
