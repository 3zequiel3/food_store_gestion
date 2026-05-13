## Why

El backend del catálogo está completo y testeado (521 tests verdes). Sin UI, ningún flujo del cliente es verificable end-to-end. Este change introduce la primera pantalla pública funcional: el catálogo de productos con filtros, búsqueda, paginación y detalle de producto, validando el contrato completo de `GET /api/v1/productos` y `GET /api/v1/productos/{id}` con una UI real.

## What Changes

- Nueva feature `features/products/` con servicio, hooks TanStack Query, tipos y componentes.
- Nueva página `pages/client/CatalogPage.tsx` — listado público de productos con filtros combinados.
- Nueva página `pages/client/ProductDetailPage.tsx` — detalle de un producto con categorías, ingredientes y botón de agregar al carrito.
- Componentes de filtro: `CategoryFilter`, `SearchBar`, `AllergenFilter`, `ActiveFilterChips`.
- Componente `ProductCard` y `ProductGrid` con skeleton loaders.
- Integración con `useCartStore` (ya implementado) para agregar ítems desde el catálogo y el detalle.
- Nuevas rutas `/catalogo` y `/catalogo/:id` en el árbol de `AppRoute.tsx` (bajo `ClienteLayout`).
- Endpoints registrados en `lib/constants/endpoints.ts`.

## Capabilities

### New Capabilities

- `products-frontend`: UI del catálogo público — listado con filtros combinados (categoría recursiva, búsqueda, alérgenos, sin_categoria), paginación, detalle de producto, integración con carrito.

### Modified Capabilities

- `routing-guards`: Agregar rutas `/catalogo` y `/catalogo/:id` al árbol de rutas públicas bajo `ClienteLayout`.

## Impact

- **Archivos nuevos**: `frontend/src/features/products/**`, `frontend/src/pages/client/CatalogPage.tsx`, `frontend/src/pages/client/ProductDetailPage.tsx`.
- **Archivos modificados**: `frontend/src/router/AppRoute.tsx` (nuevas rutas), `frontend/src/lib/constants/endpoints.ts` (nuevos endpoints), posiblemente `frontend/src/components/layout/Sidebar.tsx` (link al catálogo).
- **Dependencias ya instaladas**: TanStack Query, Zustand, Axios, Lucide React, Tailwind — ninguna dependencia nueva requerida.
- **API consumida**: `GET /api/v1/productos` (con params `page`, `limit`, `categoria_id`, `search`, `disponible`, `excluir_alergenos`, `excluir_alergeno_ids`, `sin_categoria`) y `GET /api/v1/productos/{id}` y `GET /api/v1/categorias?solo_hojas=true`.
