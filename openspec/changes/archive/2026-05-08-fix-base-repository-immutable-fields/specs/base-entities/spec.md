## ADDED Requirements

### Requirement: BaseRepository protects immutable audit fields
The `update()` method of `BaseRepository` MUST NOT overwrite the `id` or `creado_en` fields of any entity, even if a caller passes them as keyword arguments. These fields are immutable after the row is inserted.

#### Scenario: `update()` cannot overwrite `creado_en`
- **GIVEN** a `Usuario` row inserted at timestamp `T0` (`creado_en = T0`)
- **WHEN** `repo.update(user.id, creado_en=T1)` is called with `T1 != T0`
- **THEN** the persisted `creado_en` value remains `T0`
- **AND** no exception is raised (the caller's kwarg is silently ignored)

#### Scenario: `update()` cannot overwrite `id`
- **GIVEN** a `Usuario` row with `id = N`
- **WHEN** a caller invokes `repo.update(N, **payload)` with a `payload` dict that contains `"id": 999999`
- **THEN** the call raises `TypeError` (the method signature has `id` as a positional parameter, so it collides with the splatted kwarg)
- **AND** the persisted `id` remains `N`
- **AND** no row exists with `id = 999999`
- **AND** the row is not otherwise mutated
