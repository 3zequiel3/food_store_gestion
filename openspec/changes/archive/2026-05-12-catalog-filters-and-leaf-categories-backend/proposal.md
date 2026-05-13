## Why

El backend actual del catálogo (Sprint 3, ya archivado) tiene dos gaps reales para soportar UX estilo MercadoLibre del Sprint 7 (`products-frontend-catalog`): (1) `GET /productos?categoria_id=X` matchea ID exacto y no descendientes, así que clickear "Bebidas" no muestra "Coca", y (2) `excluir_alergenos` es booleano global, no permite excluir alérgenos específicos del checklist del usuario. Además, hoy el modelo deja asignar productos a categorías raíz con hijas (ej. cerveza directo en "Bebidas" en vez de "Bebidas → Alcohólicas"), lo que rompe la coherencia jerárquica. Este change cierra esos huecos antes del frontend, para que Sprint 7 consuma un backend ya correcto.

## What Changes

- **GET /productos**: `categoria_id` ahora matchea la categoría Y sus descendientes recursivamente (CTE en repository).
- **GET /productos**: nuevo query param `excluir_alergeno_ids: list[int]` que excluye productos con al menos un ingrediente no removible cuyo ID esté en la lista. El viejo `excluir_alergenos=true` se mantiene como atajo backward-compat.
- **GET /productos**: nuevo query param `sin_categoria=true` para vista admin "productos sin categorizar".
- **POST /productos** y **PUT /productos/{id}/categorias**: validación leaf-only — rechazan asignar productos a categorías que tienen hijas activas (422 con nombres de las hijas).
- **Hook auto-`disponible=false`**: tras cualquier mutación de categorías de un producto, si queda con cero categorías hoja activas → `disponible=false` automático con log.
- **POST /categorias**: rechaza crear hija de un padre que tiene productos activos (Opción A del análisis — sin estados zombie ni cascadeo mágico).
- **GET /categorias?solo_hojas=true**: nuevo modo que devuelve lista plana de categorías sin hijas activas, para el `<select>` de asignación admin. Sin param sigue devolviendo árbol recursivo.
- **GET /ingredientes?es_alergeno=true**: ya existe en código (confirmado en `ingredients/router.py:53`); la tarea es documentarlo en el spec.

Sin cambios de schema: ninguna migración necesaria — toda la lógica nueva trabaja sobre tablas y columnas existentes (`product_categories`, `product_ingredients.es_removible`, `categories.padre_id`, `ingredients.es_alergeno`).

## Capabilities

### New Capabilities

(none — todo es extensión de capabilities ya vivas)

### Modified Capabilities

- `products`: nuevos filtros de listado (`categoria_id` recursivo, `excluir_alergeno_ids`, `sin_categoria`), validación leaf-only en create + replace_categorias, hook de auto-`disponible=false`.
- `categories`: nuevo query param `solo_hojas=true` en `GET /categorias`, guard contra crear hija si el padre tiene productos activos.
- `ingredients`: formaliza el filtro existente `?es_alergeno=true` como contrato público (lo usa Sprint 7 para el multi-select de alérgenos).

## Impact

- `backend/features/products/repository.py` — `list_paginated_with_filters` extendido (CTE recursivo, NOT EXISTS por ingrediente_id, NOT EXISTS para sin_categoria); nuevo `count_leaf_active_categories(product_id)`.
- `backend/features/products/service.py` — helper `_validate_categorias_are_leaves(...)` invocado en `create()` y `set_categorias()`; hook `_auto_disable_if_no_leaf_categoria(...)` post-mutación.
- `backend/features/products/router.py` — query params `excluir_alergeno_ids: list[int]` y `sin_categoria: bool`.
- `backend/features/categories/service.py` — guard `create()` contra padre con productos activos.
- `backend/features/categories/repository.py` — helper `list_leaf_categories()` (flat).
- `backend/features/categories/router.py` — query param `solo_hojas: bool`.
- `backend/features/ingredients/router.py` — sin cambios (solo doc en spec).
- Tests: integración + unit en `backend/tests/` siguiendo TDD para cada feature.
- Seed/migración: audit de productos seed asignados a categorías raíz (corrección puntual si aparecen — no migración estructural).
