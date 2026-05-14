# Proposal: Move es_removible from pivot to Ingrediente model + admin profile

## Intent

`es_removible` currently lives on the `ProductoIngrediente` pivot table (per-product-per-ingredient flag). It needs to become a global attribute on the `Ingrediente` model itself — a single "is removable" flag editable from the ingredients admin page. The catalog filters by `es_removible` to show removable ingredients to clients; without the ability to set this flag on ingredients, those filters don't work.

Additionally, the admin sidebar footer links to `/admin/usuarios` (list of all users) instead of a self-profile view. Admins need a "my profile" route like clients already have.

## Scope

### In Scope
- Add `es_removible: Mapped[bool]` column to `Ingrediente` model and `ingredients` table
- Remove `es_removible` column from `ProductoIngrediente` model and `product_ingredients` table
- Update all backend schemas, repos, services, routers that reference `es_removible` on the pivot
- Update frontend types, form, row, and admin ingredients page for the new field
- Create admin self-profile view (reuse or adapt client profile form)
- Fix sidebar footer link for admin role

### Out of Scope
- Changing the business rule that an ingredient is globally removable (this is the desired behavior)
- ProductDetailPage — DTO shape (`IngredienteAsociadoRead`) stays the same, no frontend change needed there
- Any changes to allergen exclusion logic semantics (only the column source changes, not the filter behavior)

## Capabilities

### New Capabilities
- `admin-self-profile`: Admin self-service profile view and sidebar footer link fix

### Modified Capabilities
- `ingredients`: Add `es_removible` field to ingredient CRUD (create, read, update, list filter)
- `products`: Remove `es_removible` from pivot-based operations; source it from `Ingrediente` in read responses
- `admin-ingredientes`: Add `es_removible` column to admin table and checkbox to create/edit form

## Approach

1. **Alembic migration**: Add `es_removible BOOLEAN NOT NULL DEFAULT false` to `ingredients`, drop column from `product_ingredients`
2. **Backend models**: Add column to `Ingrediente`, remove from `ProductoIngrediente`
3. **Backend schemas**: Add to `IngredienteCreate/Update/Read`; remove from `AsociarIngrediente`; keep in `IngredienteAsociadoRead` (now sourced from `Ingrediente.es_removible`)
4. **Backend repository**: Rewrite allergen-exclusion subqueries to use `Ingrediente.es_removible`; simplify `list_ingredientes()` return type
5. **Backend service**: Update methods that unpack `(Ingrediente, bool)` tuples; remove `es_removible` param from association methods
6. **Backend router**: Remove `es_removible` from association endpoint payload processing
7. **Integration tests**: Rewrite setup — removability set on ingredient, not association
8. **Frontend**: Add `es_removible` to types, form checkbox, row badge, table header
9. **Admin profile**: Create self-profile view for admin, fix sidebar footer link

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/features/catalog/models.py` | Modified | Add `es_removible` to `Ingrediente` |
| `backend/features/products/models.py` | Modified | Remove `es_removible` from `ProductoIngrediente` |
| `backend/features/ingredients/schemas.py` | Modified | Add `es_removible` to CRUD schemas |
| `backend/features/products/schemas.py` | Modified | Remove from `AsociarIngrediente`, keep in `IngredienteAsociadoRead` |
| `backend/features/products/repository.py` | Modified | Rewrite allergen subqueries, simplify return types |
| `backend/features/products/service.py` | Modified | Update tuple unpacking, remove param from association methods |
| `backend/features/products/router.py` | Modified | Remove `es_removible` from association payloads |
| `backend/alembic/versions/` | New | Migration: add to ingredients, remove from product_ingredients |
| `tests/integration/test_catalog_filters.py` | Modified | Rewrite test setup |
| `tests/integration/test_products.py` | Modified | Rewrite test setup |
| `frontend/src/features/ingredientes/types.ts` | Modified | Add `es_removible` to types |
| `frontend/src/features/ingredientes/components/IngredienteFormModal.tsx` | Modified | Add checkbox |
| `frontend/src/features/ingredientes/components/IngredienteRow.tsx` | Modified | Add badge/toggle |
| `frontend/src/features/ingredientes/pages/AdminIngredientesPage.tsx` | Modified | Add table header |
| `frontend/src/features/admin/` | New | Admin profile page component |
| `frontend/src/features/navigation/` | Modified | Fix sidebar footer link |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Data loss of existing `es_removible` values in pivot | Medium | Migration should log/count affected rows; current behavior is mostly default=false so impact is low |
| Allergen exclusion filter breaks during migration | Low | Rewrite subqueries to use `Ingrediente.es_removible` — same logic, different column source |
| Frontend breaks if `IngredienteAsociadoRead` shape changes | Low | Keep `es_removible` in the read DTO — only the source changes, not the output |
| Admin profile duplicates client profile code | Medium | Extract shared profile form component or reuse with role-aware rendering |

## Rollback Plan

1. Revert the Alembic migration (`alembic downgrade -1`) — restores `es_removible` on `product_ingredients`, removes from `ingredients`
2. Revert all code changes via `git revert`
3. Re-run `alembic upgrade head` to restore previous schema
4. For admin profile: remove the new route and restore sidebar footer link

## Dependencies

- None — this change is independent of the current Sprint 5/6 changes. It touches already-archived capabilities (ingredients, products, admin-ingredientes).

## Success Criteria

- [ ] `es_removible` column exists on `ingredients` table, removed from `product_ingredients`
- [ ] Ingredient CRUD API accepts and returns `es_removible`
- [ ] Product detail endpoint returns `es_removible` on each ingredient (sourced from `Ingrediente`)
- [ ] Catalog allergen exclusion filter works correctly with the new column source
- [ ] Admin ingredients page shows "Removible" column with toggle/checkbox
- [ ] Admin can create/edit ingredients with `es_removible` flag
- [ ] Admin has a self-profile route accessible from sidebar footer
- [ ] All integration tests pass
