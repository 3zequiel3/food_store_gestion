## Context

El sistema ya implementa `require_role("ADMIN", "STOCK")` en todos los endpoints de mutación de catálogo. El RBAC dinámico de pedidos (`_is_admin_view()` en `OrderService`) también incluye ADMIN. Este change cierra formalmente US-064/US-065 e implementa RN-CA10: el parámetro `incluir_eliminados` para que los admins puedan ver registros con soft-delete en listados.

## Goals

- Implementar `incluir_eliminados: bool = False` en `GET /api/v1/productos` y `GET /api/v1/ingredientes`.
- Solo ADMIN puede obtener resultados con `incluir_eliminados=true`; otros roles lo ignoran (filtran siempre activos).
- Agregar tests de integración explícitos para US-064 y US-065.

## Non-Goals

- No se modifican los permisos de escritura (ya correctos).
- No se toca el endpoint `GET /api/v1/categorias` (árbol jerárquico, public).
- No se implementa paginación de eliminados para el árbol de categorías.
- No se crea un endpoint `/admin/catalogo` separado.

## Decisions

### D1: `incluir_eliminados` solo efectivo para ADMIN

El query param `incluir_eliminados` existe en el endpoint pero es ignorado silenciosamente si el usuario no es ADMIN (o si no hay autenticación). No se retorna 403 — se filtra igual que sin el param. Esto evita information disclosure: un CLIENT que manda `?incluir_eliminados=true` simplemente ve el catálogo público normal.

Implementación: el router pasa `incluir_eliminados` al service junto con el `current_user` opcional. El service verifica el rol; si no es ADMIN, pone `incluir_eliminados=False` antes de llamar al repository.

### D2: `get_optional_user` para mantener endpoint público

`GET /productos` y `GET /ingredientes` son endpoints públicos. Usar `get_optional_user` (ya existe en `dependencies.py`) permite recibir el usuario si está autenticado sin requerir auth. Si `user is None` → `incluir_eliminados` siempre `False`.

### D3: Repository — filtro condicional en `list_paginated`

El repository recibe `incluir_eliminados: bool`. Si `True`: omite el filtro `eliminado_en IS NULL`. Si `False` (default): comportamiento actual. No se toca otra lógica.

### D4: Categorías — sin cambio

El árbol de categorías ya excluye soft-deleted en el service. RN-CA10 no se aplica al árbol porque la jerarquía puede quedar inconsistente con nodos eliminados mezclados. Si en el futuro se necesita, es un change separado.

### D5: Tests TDD

Tests primero (rojo), luego implementación (verde). Tests deben cubrir:
- ADMIN puede llamar a mutaciones de catálogo (US-064) — ya existen, agregar los que falten
- ADMIN ve pedidos (US-065) — verificar cobertura en test_visualization
- ADMIN con `incluir_eliminados=true` recibe soft-deleted en listados
- CLIENT/STOCK/sin-auth con `incluir_eliminados=true` NO ve soft-deleted

## Risks

- R1: El service de productos recibe `current_user` opcional — hay que tener cuidado de no romper la firma existente. Solución: agregar parámetro con default `None`.
- R2: Si `listar_productos` o `listar_ingredientes` tienen tests que no esperan el nuevo parámetro de router, pueden fallar. Solución: los tests existentes no pasan `incluir_eliminados`, así que el default `False` los mantiene verdes.
