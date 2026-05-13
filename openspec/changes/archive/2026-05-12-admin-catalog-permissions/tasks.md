# Tasks: admin-catalog-permissions

Sprint 6 #19 — US-064, US-065, RN-CA10

## 1. Tests TDD — `incluir_eliminados` en productos (rojo)

- [x] 1.1 En `test_products.py`: agregar clase `TestIncluidoEliminados` con tests:
  - [x] 1.1.a ADMIN + `incluir_eliminados=true` → recibe productos soft-deleted en el listado
  - [x] 1.1.b CLIENT + `incluir_eliminados=true` → NO recibe soft-deleted (default público)
  - [x] 1.1.c Sin auth + `incluir_eliminados=true` → NO recibe soft-deleted
  - [x] 1.1.d STOCK + `incluir_eliminados=true` → NO recibe soft-deleted

## 2. Tests TDD — `incluir_eliminados` en ingredientes (rojo)

- [x] 2.1 En `test_ingredients.py`: agregar clase `TestIncluidoEliminados` con tests:
  - [x] 2.1.a ADMIN + `incluir_eliminados=true` → recibe ingredientes soft-deleted
  - [x] 2.1.b CLIENT + `incluir_eliminados=true` → NO recibe soft-deleted
  - [x] 2.1.c Sin auth + `incluir_eliminados=true` → NO recibe soft-deleted

## 3. Tests TDD — cobertura explícita US-065 (ADMIN en pedidos)

- [x] 3.1 En `test_visualization_list.py`: ADMIN puede listar todos los pedidos (ya cubierto — `test_admin_role_ve_todos` existe).
- [x] 3.2 En `test_router_estado.py`: agregar fixture `auth_headers_admin` + 2 tests: ADMIN cancela PENDIENTE y ADMIN avanza CONFIRMADO → EN_PREPARACION.

## 4. Implementación — repository productos

- [x] 4.1 En `backend/features/products/repository.py`: agregar `incluir_eliminados: bool = False` a `list_paginated_with_filters`. Si `False`: filtrar `eliminado_en IS NULL` (comportamiento actual). Si `True`: omitir ese filtro.

## 5. Implementación — service productos

- [x] 5.1 En `backend/features/products/service.py`: agregar `current_user: Optional[Usuario] = None` e `incluir_eliminados: bool = False` a `list_paginated`. Si el usuario no tiene rol ADMIN, forzar `incluir_eliminados=False`. Propagar al repository.

## 6. Implementación — router productos

- [x] 6.1 En `backend/features/products/router.py`: agregar `incluir_eliminados: bool = Query(False)` a `listar_productos`. Agregar `current_user: Optional[Usuario] = Depends(get_optional_user)`. Pasar ambos al service.

## 7. Implementación — repository ingredientes

- [x] 7.1 En `backend/features/ingredients/repository.py`: agregar `incluir_eliminados: bool = False` a `list_paginated`. Filtro condicional igual que productos.

## 8. Implementación — service ingredientes

- [x] 8.1 En `backend/features/ingredients/service.py`: agregar `current_user: Optional[Usuario] = None` e `incluir_eliminados: bool = False` a `list_paginated`. Verificar rol ADMIN, propagar al repository.

## 9. Implementación — router ingredientes

- [x] 9.1 En `backend/features/ingredients/router.py`: agregar `incluir_eliminados: bool = Query(False)` a `listar_ingredientes`. Agregar `current_user: Optional[Usuario] = Depends(get_optional_user)`. Pasar ambos al service.

## 10. Verde — correr tests y verificar

- [x] 10.1 9/9 tests nuevos pasan (verde).
- [x] 10.2 Tests de US-065 (ADMIN en pedidos) pasan (verde).
- [x] 10.3 Suite completa: 449 passed, 9 skipped, 0 failures — sin regresiones.

## 11. Actualizar CHANGES.md

- [x] 11.1 Sprint 6 marcado como 🔄 En progreso con admin-catalog-permissions ✅ en `docs/CHANGES.md`.
