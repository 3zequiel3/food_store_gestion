# Delta for database-migrations

## ADDED Requirements

### Requirement: Migration moves es_removible from pivot to Ingrediente

The system SHALL provide an Alembic migration that: (1) adds `es_removible BOOLEAN NOT NULL DEFAULT false` to the `ingredients` table, (2) drops the `es_removible` column from the `product_ingredients` table. The migration SHALL log the count of affected rows before dropping the pivot column. `down_revision` SHALL point to the latest existing migration.

#### Scenario: Upgrade adds column to ingredients and drops from product_ingredients

- **WHEN** `alembic upgrade head` is executed
- **THEN** the `ingredients` table has `es_removible BOOLEAN NOT NULL DEFAULT false` AND the `product_ingredients` table no longer has `es_removible`

#### Scenario: Existing ingredients get default false

- **GIVEN** the `ingredients` table has rows before migration
- **WHEN** `alembic upgrade head` is executed
- **THEN** those rows have `es_removible = false`

#### Scenario: Downgrade reverses the operation

- **WHEN** `alembic downgrade -1` is executed
- **THEN** `es_removible` is removed from `ingredients` AND re-added to `product_ingredients` with `DEFAULT false`

#### Scenario: Migration logs affected pivot rows

- **WHEN** the upgrade runs
- **THEN** a log message reports how many `product_ingredients` rows had `es_removible = true` before the column is dropped
