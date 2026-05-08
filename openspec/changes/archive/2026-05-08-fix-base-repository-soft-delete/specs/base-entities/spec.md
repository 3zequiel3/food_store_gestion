## ADDED Requirements

### Requirement: BaseRepository enforces soft-delete semantics via `eliminado_en`
The `BaseRepository` SHALL detect at construction time whether the bound model declares an `eliminado_en` column. When present, default read paths MUST exclude soft-deleted rows and `delete()` MUST set the timestamp instead of physically removing the row. When absent, `delete()` MUST fall back to physical deletion.

#### Scenario: Default queries exclude soft-deleted rows for models with `eliminado_en`
- **WHEN** a repository is instantiated with a model that inherits from `BaseModel` (which declares `eliminado_en`)
- **AND** a row is soft-deleted (its `eliminado_en` column is non-null)
- **THEN** `read(id)`, `list()`, and `count()` MUST NOT return or count that row
- **AND** the row MUST remain physically present in the underlying table

#### Scenario: `delete()` performs soft delete on models with `eliminado_en`
- **WHEN** `repo.delete(id)` is called on a model that has the `eliminado_en` column
- **THEN** the row's `eliminado_en` is set to the current UTC timestamp
- **AND** the row is NOT physically removed from the table
- **AND** the method returns `True`

#### Scenario: `delete()` falls back to hard delete on models without `eliminado_en`
- **WHEN** `repo.delete(id)` is called on a model that does NOT declare an `eliminado_en` column (e.g. catalog tables like `Rol`)
- **THEN** the row is physically removed from the table via `session.delete(...)`
- **AND** the method returns `True`

#### Scenario: `hard_delete()` always removes the row physically
- **WHEN** `repo.hard_delete(id)` is called
- **THEN** the row is physically removed regardless of whether the model declares `eliminado_en`
- **AND** the method returns `True` if the row existed, `False` otherwise
