## Context

El backend expone `GET /api/v1/productos` con 8 query params de filtrado (incluidos los nuevos `excluir_alergeno_ids`, `sin_categoria`, categoría recursiva via CTE) y `GET /api/v1/productos/{id}` con detalle completo. Los ENDPOINTS ya están definidos en `endpoints.ts`. El router ya tiene el slot `/cliente/catalogo` como `PlaceholderPage` dentro del `RoleGuard(['CLIENT'])`. El `useCartStore` ya expone `addItem(item, cantidad)`. TanStack Query está configurado con `staleTime: 30_000`.

## Goals / Non-Goals

**Goals:**
- Reemplazar el `PlaceholderPage` de `/cliente/catalogo` con la página real de catálogo paginado.
- Agregar ruta `/cliente/catalogo/:id` para el detalle del producto.
- Implementar filtros combinados: categoría (dropdown con hojas), búsqueda (text debounced), alérgenos (checkboxes), paginación.
- Integrar el botón "Agregar al carrito" tanto en `ProductCard` como en `ProductDetailPage`.
- Mostrar skeleton loaders durante la carga.

**Non-Goals:**
- Filtro de rango de precio (no está en el backend actual).
- Reviews o ratings de productos.
- Modo admin de gestión de productos (sprint separado).
- Checkout (sprint 9).

## Decisions

### D1 — Estado de filtros en URL (`useSearchParams`), no en useState

Los filtros se sincronizan con la URL via `useSearchParams` de React Router. Cambiar un filtro hace `setSearchParams(...)`, no `setState(...)`.

**Alternativa**: `useState` local en CatalogPage — más simple, pero el usuario pierde la búsqueda al navegar al detalle y volver.

**Decisión**: URL. El queryKey de TanStack Query deriva directamente de los searchParams parseados, así el cache se invalida solo cuando cambia la URL.

**Consecuencia**: `queryKey: ['products', { page, limit, categoria_id, search, disponible, excluir_alergenos, excluir_alergeno_ids }]` — el cache es por combinación de filtros.

### D2 — Hook `useProducts(filters)` con `useQuery`, no `useInfiniteQuery`

El backend devuelve `{ items, total, page, limit }` — paginación clásica. Se implementa con `useQuery` y un componente `Pagination` con números de página.

**Alternativa**: `useInfiniteQuery` con scroll infinito — mejor UX mobile, pero la api tiene pagination basada en `page`, no en cursor. Se puede agregar después.

**Decisión**: `useQuery` con `keepPreviousData: true` para evitar flicker al cambiar de página.

### D3 — `useLeafCategories()` separado del listado de productos

El dropdown de categorías usa `GET /api/v1/categorias?solo_hojas=true` — una query independiente con `staleTime: 5 * 60_000` (5 min, cambia poco). No se mezcla con la query de productos.

### D4 — Estructura de archivos: `features/products/`

```
frontend/src/features/products/
├── components/
│   ├── ProductCard.tsx          ← Card con imagen, nombre, precio, botón carrito
│   ├── ProductGrid.tsx          ← Grid con skeleton loaders
│   ├── ProductCardSkeleton.tsx  ← Skeleton para ProductCard
│   ├── filters/
│   │   ├── SearchBar.tsx        ← Input debounced (300ms)
│   │   ├── CategoryFilter.tsx   ← Select de categorías hoja
│   │   ├── AllergenFilter.tsx   ← Checkboxes excluir_alergenos + excluir_alergeno_ids
│   │   └── ActiveFilterChips.tsx ← Chips de filtros activos con × para remover
│   └── Pagination.tsx           ← Navegación de páginas
├── hooks/
│   ├── useProducts.ts           ← useQuery(['products', filters])
│   ├── useProduct.ts            ← useQuery(['products', id])
│   └── useLeafCategories.ts     ← useQuery(['categories', 'leaves'])
├── services/
│   └── products.service.ts      ← getProducts(params), getProduct(id)
└── types/
    └── products.types.ts        ← ProductoRead, ProductoDetail, PaginatedProductos, ProductFilters
```

Páginas en `pages/client/`:
```
CatalogPage.tsx      ← compone filtros + ProductGrid + Pagination
ProductDetailPage.tsx ← detalle completo + botón carrito
```

### D5 — Debounce en SearchBar: 300ms, sin submit manual

El `SearchBar` usa un `useState` interno que actualiza `searchParams` con 300ms de debounce. No hay botón "Buscar". La query se dispara automáticamente al dejar de escribir.

### D6 — `AllergenFilter`: checkbox único + multi-select de ingredientes

Dos controles separados pero en el mismo componente:
1. Checkbox `excluir_alergenos: bool` — excluye todos los alérgenos no-removibles.
2. Multi-select de ingredientes (obtenido de `GET /api/v1/ingredientes?es_alergeno=true`) — popula `excluir_alergeno_ids[]`.

Semántica AND confirmada por el backend.

### D7 — Integración con carrito desde ProductCard y ProductDetailPage

`ProductCard` tiene un botón "+" que llama `useCartStore.getState().addItem(...)` directamente (sin hook de React, acceso directo al store). Si el producto no está disponible (`disponible: false`) o sin stock (`stock_cantidad: 0`), el botón está deshabilitado con tooltip "Sin stock".

`ProductDetailPage` tiene un selector de cantidad + botón "Agregar al carrito" más prominente.

### D8 — Routing: reemplazar PlaceholderPage, agregar `:id`

En `AppRoute.tsx`, dentro del bloque `RoleGuard(['CLIENT'])`:

```tsx
// ANTES:
<Route path="catalogo" element={<PlaceholderPage ... />} />

// DESPUÉS:
<Route path="catalogo" element={<CatalogPage />} />
<Route path="catalogo/:id" element={<ProductDetailPage />} />
```

### D9 — Skeleton loaders en lugar de spinner global

`ProductGrid` renderiza 12 `ProductCardSkeleton` mientras `isLoading` es `true`. Con `keepPreviousData: true`, los skeletons solo aparecen en la carga inicial, no al cambiar de página (el dato anterior permanece visible durante el fetch).

## Risks / Trade-offs

- [RoleGuard CLIENT] La ruta `/cliente/catalogo` está dentro del `RoleGuard(['CLIENT'])`. Si queremos que el catálogo sea accesible para visitantes no autenticados en el futuro, hay que mover la ruta fuera del guard. Por ahora la spec dice que el catálogo es público (`GET /productos` no requiere auth), pero la UI sí requiere login. → Mitigación: documentar en el PR, fácil de mover después.
- [Debounce + staleTime] Con `staleTime: 30_000` y debounce de 300ms, una búsqueda rápida puede servir datos cacheados de 30 segundos atrás. → Mitigación: aceptable para un catálogo; si cambia el requisito, se puede reducir `staleTime` para la query de productos.
- [excluir_alergeno_ids + ingredientes] Requiere una query adicional a `GET /ingredientes?es_alergeno=true` para el multi-select. Si hay muchos ingredientes alérgenos, el dropdown puede crecer. → Mitigación: el catálogo de ingredientes es acotado en este dominio; no se pagina.
