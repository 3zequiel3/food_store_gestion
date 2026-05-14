# Design: Move es_removible from pivot to Ingrediente + Admin Profile

## Technical Approach

Column-level refactor: migrate `es_removible` from the `product_ingredients` pivot table to the `ingredients` catalog table. This changes the semantics from per-product-per-ingredient to global-per-ingredient. The `IngredienteAsociadoRead` DTO shape is preserved — only the column source changes. A secondary scope adds an admin self-profile route.

## Architecture Decisions

### Decision: Migration strategy — two-step add/drop

**Choice**: Single Alembic migration that (1) adds `es_removible` to `ingredients`, (2) drops it from `product_ingredients`. No data backfill — current values are mostly `false` (default).

**Alternatives considered**:
- Two separate migrations (add then drop) — more granular but unnecessary complexity.
- Backfill from pivot to ingredients before drop — requires a data migration step; overkill since default=false covers existing rows.

**Rationale**: Single atomic migration matches the existing pattern (see `20260508_0001`). The `server_default=false` makes the add-column safe for existing rows. The drop-column is safe because no code will reference it after deployment.

### Decision: IngredienteAsociadoRead stays on products/schemas.py

**Choice**: Keep `IngredienteAsociadoRead` in `features/products/schemas.py` but change construction from tuple unpacking to `from_attributes=True` on the `Ingrediente` model directly.

**Alternatives considered**:
- Move to `features/ingredients/schemas.py` — would create circular import risk (products imports ingredients schemas).
- Keep manual construction — unnecessary complexity now that `es_removible` is on the model.

**Rationale**: `from_attributes=True` on `Ingrediente` can now populate `es_removible` directly. The DTO stays in products because it's a product-context read model.

### Decision: list_ingredientes return type simplification

**Choice**: Change `list_ingredientes()` from `list[tuple[Ingrediente, bool]]` to `list[Ingrediente]`. The `es_removible` flag is now an attribute of `Ingrediente` itself.

**Alternatives considered**:
- Keep tuple return for backward compat — adds unnecessary indirection.
- Return `list[IngredienteAsociadoRead]` from repo — violates layer separation (repo shouldn't return Pydantic schemas).

**Rationale**: Simplifies the entire chain: repo returns `list[Ingrediente]`, service passes through, router constructs DTO via `from_attributes`. Eliminates all `(ing, removible)` tuple unpacking.

### Decision: Admin profile — reuse ProfilePage component

**Choice**: Create `AdminProfilePage` that reuses the existing `ProfileForm` and `PasswordModal` from `features/user-profile/`. Add route `/admin/perfil`. Fix `SidebarFooter` link from `/admin/usuarios` to `/admin/perfil`.

**Alternatives considered**:
- Single role-agnostic `/perfil` route — would need to detect role and render different layouts; more complex.
- Copy-paste profile form — code duplication, maintenance burden.

**Rationale**: The profile form is role-agnostic (nombre, apellido, email, password). A thin wrapper page under the admin layout is the simplest path. The `SidebarFooter` fix is a one-line change.

## Data Flow

```
BEFORE:
  Producto ──M:N──> ProductoIngrediente(es_removible) ──FK──> Ingrediente
  Repo: SELECT Ingrediente, ProductoIngrediente.es_removible
  Router: tuple unpack (ing, removible)

AFTER:
  Producto ──M:N──> ProductoIngrediente ──FK──> Ingrediente(es_removible)
  Repo: SELECT Ingrediente (es_removible is attribute)
  Router: IngredienteAsociadoRead.model_validate(ing)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/alembic/versions/YYYYMMDD_NNNN_move_es_removible_to_ingredients.py` | Create | Add column to ingredients, drop from product_ingredients |
| `backend/features/catalog/models.py` | Modify | Add `es_removible: Mapped[bool]` to `Ingrediente` |
| `backend/features/products/models.py` | Modify | Remove `es_removible` from `ProductoIngrediente` |
| `backend/features/ingredients/schemas.py` | Modify | Add `es_removible` to `IngredienteCreate`, `IngredienteUpdate`, `IngredienteRead` |
| `backend/features/products/schemas.py` | Modify | Remove `es_removible` from `AsociarIngrediente`; update `IngredienteAsociadoRead` to use `from_attributes` |
| `backend/features/products/repository.py` | Modify | Rewrite allergen subqueries to use `Ingrediente.es_removible`; simplify `list_ingredientes` return type; simplify `add_ingrediente` signature |
| `backend/features/products/service.py` | Modify | Remove `es_removible` param from `add_ingrediente`; change tuple unpacking throughout |
| `backend/features/products/router.py` | Modify | Remove `es_removible` from association payload processing; use `from_attributes` for DTO |
| `backend/features/ingredients/repository.py` | Modify | Add `es_removible` filter to `list_paginated` |
| `backend/features/ingredients/service.py` | Modify | Pass `es_removible` to `repo.create()` |
| `backend/features/ingredients/router.py` | Modify | Add `es_removible` query param to list endpoint |
| `frontend/src/features/ingredientes/types/ingredientes.types.ts` | Modify | Add `es_removible` to `IngredienteRead`, `IngredienteCreate`, `IngredienteUpdate` |
| `frontend/src/features/ingredientes/components/IngredienteFormModal.tsx` | Modify | Add "Es removible" checkbox |
| `frontend/src/features/ingredientes/components/IngredienteRow.tsx` | Modify | Add removible badge/toggle column |
| `frontend/src/pages/admin/AdminIngredientesPage.tsx` | Modify | Add "Removible" table header |
| `frontend/src/pages/admin/AdminProfilePage.tsx` | Create | Admin self-profile page (reuses ProfileForm + PasswordModal) |
| `frontend/src/components/layout/SidebarFooter.tsx` | Modify | Change `profileRoute` from `/admin/usuarios` to `/admin/perfil` for admin roles |
| `frontend/src/router/AppRoute.tsx` | Modify | Add `/admin/perfil` route |
| `backend/tests/integration/test_catalog_filters.py` | Modify | Rewrite test setup: set `es_removible` on ingredient, not association |
| `backend/tests/integration/test_products.py` | Modify | Rewrite test setup: set `es_removible` on ingredient, not association |

## Interfaces / Contracts

### Alembic Migration

```python
def upgrade():
    op.add_column("ingredients", sa.Column("es_removible", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_column("product_ingredients", "es_removible")

def downgrade():
    op.add_column("product_ingredients", sa.Column("es_removible", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_column("ingredients", "es_removible")
```

### Model Changes

```python
# catalog/models.py — Ingrediente
es_removible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

# products/models.py — ProductoIngrediente
# REMOVE: es_removible column entirely
```

### Schema Changes

```python
# ingredients/schemas.py
class IngredienteCreate(BaseModel):
    nombre: str
    es_alergeno: bool = False
    es_removible: bool = False  # NEW

class IngredienteUpdate(BaseModel):
    nombre: str | None = None
    es_alergeno: bool | None = None
    es_removible: bool | None = None  # NEW

class IngredienteRead(BaseModel):
    id: int
    nombre: str
    es_alergeno: bool
    es_removible: bool  # NEW
    creado_en: datetime
    actualizado_en: datetime
    model_config = {"from_attributes": True}

# products/schemas.py
class AsociarIngrediente(BaseModel):
    ingrediente_id: int
    # REMOVED: es_removible

class IngredienteAsociadoRead(BaseModel):
    id: int
    nombre: str
    es_alergeno: bool
    es_removible: bool
    model_config = ConfigDict(from_attributes=True)  # NEW — auto-populate from Ingrediente
```

### Repository Changes

```python
# products/repository.py — list_ingredientes
def list_ingredientes(self, producto_id: int) -> list[Ingrediente]:
    """Return Ingrediente objects for a product (es_removible is now on model)."""
    query = (
        select(Ingrediente)
        .join(ProductoIngrediente, ProductoIngrediente.ingredient_id == Ingrediente.id)
        .where(
            ProductoIngrediente.product_id == producto_id,
            ProductoIngrediente.eliminado_en.is_(None),
            Ingrediente.eliminado_en.is_(None),
        )
    )
    return list(self.session.execute(query).scalars().all())

# products/repository.py — add_ingrediente (simplified)
def add_ingrediente(self, producto_id: int, ingrediente_id: int) -> ProductoIngrediente:
    """es_removible removed from signature — it's on Ingrediente now."""

# products/repository.py — allergen subqueries
# Change: pi.c.es_removible.is_(False) → ing.c.es_removible.is_(False)
```

### Service Changes

```python
# products/service.py — add_ingrediente
def add_ingrediente(self, producto_id: int, ingrediente_id: int) -> tuple[ProductoIngrediente, list[Ingrediente]]:
    """No es_removible param. Return type changes from list[tuple[Ingrediente, bool]] to list[Ingrediente]."""

# products/service.py — get_detail
def get_detail(self, producto_id: int) -> tuple[Producto, list[Categoria], list[Ingrediente]]:
    """Return type: list[Ingrediente] instead of list[tuple[Ingrediente, bool]]."""

# products/service.py — set_categorias
def set_categorias(...) -> tuple[Producto, list[Categoria], list[Ingrediente]]:
    """Same simplification."""
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Ingrediente.es_removible` defaults to `False` | Model instantiation test |
| Unit | `IngredienteCreate/Update/Read` include `es_removible` | Schema validation test |
| Integration | POST `/ingredientes` with `es_removible=true` | API test with admin auth |
| Integration | GET `/productos/{id}/ingredientes` returns `es_removible` from ingredient | API test |
| Integration | Catalog filter `excluir_alergenos` uses `Ingrediente.es_removible` | Rewrite existing test setup |
| Integration | Admin ingredient page shows removible column | Frontend component test |
| Migration | Upgrade/downgrade round-trip | Alembic test |

## Migration / Rollout

1. Deploy migration + code together (single deploy).
2. Migration is additive (add column with default) then destructive (drop column).
3. Rollback: `alembic downgrade -1` restores `es_removible` on `product_ingredients`, removes from `ingredients`.
4. No feature flag needed — the column move is atomic with deployment.

## Open Questions

- [ ] Should `es_removible` be editable on existing ingredients or only settable at creation time? (Design assumes editable via update — matches `es_alergeno` pattern.)
- [ ] Data migration: if any existing `es_removible=true` values exist in `product_ingredients`, should we backfill them to the ingredient row? (Design assumes no backfill — default=false is correct for existing data.)
