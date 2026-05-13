## Why

Los endpoints de catálogo (productos, categorías, ingredientes) y pedidos requieren que el rol ADMIN tenga acceso completo equivalente al de STOCK y PEDIDOS respectivamente, para que el administrador pueda intervenir sin depender de otros gestores (US-064, US-065). Adicionalmente, RN-CA10 exige un parámetro `incluir_eliminados` en los endpoints de admin para visualizar registros con soft-delete.

## What Changes

- Verificar que `require_role("ADMIN", "STOCK")` está aplicado en todos los endpoints de escritura de catálogo (ya implementado — esta validación cierra US-064 formalmente).
- Implementar `incluir_eliminados: bool = False` como query param en los endpoints de listado de productos, categorías e ingredientes. Solo ADMIN puede activarlo (RN-CA10).
- Verificar que el RBAC dinámico de pedidos ya incluye ADMIN en `_is_admin_view()` (ya implementado — cierra US-065).
- Agregar tests de integración explícitos que verifiquen acceso ADMIN a endpoints de catálogo y pedidos (cobertura de las historias).

## Capabilities

### New Capabilities

- `admin-catalog-permissions`: Parámetro `incluir_eliminados` en listados de catálogo para rol ADMIN; tests de cobertura explícita de US-064/US-065.

### Modified Capabilities

- `catalog`: El endpoint GET /productos y GET /ingredientes reciben nuevo query param `incluir_eliminados` (solo efectivo para ADMIN).

## Impact

- `backend/features/products/router.py` — agregar `incluir_eliminados` a `listar_productos`
- `backend/features/products/service.py` — propagar `incluir_eliminados` a repository
- `backend/features/products/repository.py` — filtro condicional de soft-delete
- `backend/features/ingredients/router.py` — agregar `incluir_eliminados` a `listar_ingredientes`
- `backend/features/ingredients/service.py` — propagar flag
- `backend/features/ingredients/repository.py` — filtro condicional
- `backend/features/categories/router.py` — GET árbol ya excluye soft-deleted; sin cambio de flag aquí
- `backend/tests/integration/test_products.py` — tests ADMIN explícitos + `incluir_eliminados`
- `backend/tests/integration/test_ingredients.py` — tests ADMIN explícitos + `incluir_eliminados`
- `backend/tests/integration/test_categories.py` — tests ADMIN explícitos (ya parcialmente cubiertos)
