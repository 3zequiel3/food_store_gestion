## 1. Tipos y servicio

- [x] 1.1 Crear `frontend/src/features/products/types/products.types.ts` con tipos `ProductoRead`, `ProductoDetail`, `PaginatedProductos`, `CategoriaRead`, `IngredienteAsociadoRead`, `ProductFilters`.
- [x] 1.2 Crear `frontend/src/features/products/services/products.service.ts` con funciones `getProducts(filters: ProductFilters)` y `getProduct(id: number)` usando `apiClient` y `ENDPOINTS.productos`.
- [x] 1.3 Crear `frontend/src/features/categories/services/categories.service.ts` con función `getLeafCategories()` que llama `GET /categorias/?solo_hojas=true`.
- [x] 1.4 Crear `frontend/src/features/ingredients/services/ingredients.service.ts` con función `getAllergenIngredients()` que llama `GET /ingredientes/?es_alergeno=true`.

## 2. Hooks TanStack Query

- [x] 2.1 Crear `frontend/src/features/products/hooks/useProducts.ts` — `useQuery(['products', filters], () => getProducts(filters), { placeholderData: keepPreviousData })`.
- [x] 2.2 Crear `frontend/src/features/products/hooks/useProduct.ts` — `useQuery(['products', id], () => getProduct(id), { enabled: id > 0 })`.
- [x] 2.3 Crear `frontend/src/features/products/hooks/useLeafCategories.ts` — `useQuery(['categories', 'leaves'], getLeafCategories, { staleTime: 5 * 60_000 })`.
- [x] 2.4 Crear `frontend/src/features/ingredients/hooks/useAllergenIngredients.ts` — `useQuery(['ingredients', 'allergens'], getAllergenIngredients, { staleTime: 5 * 60_000 })`.

## 3. Componentes de filtro

- [x] 3.1 Crear `frontend/src/features/products/components/filters/SearchBar.tsx` — input de texto con debounce 300ms que actualiza `search` en `useSearchParams`. Incluir botón "×" para limpiar.
- [x] 3.2 Crear `frontend/src/features/products/components/filters/CategoryFilter.tsx` — `<select>` poblado con `useLeafCategories()`. Primera opción "Todas las categorías" (sin filtro). Al cambiar, actualiza `categoria_id` y resetea `page=1`.
- [x] 3.3 Crear `frontend/src/features/products/components/filters/AllergenFilter.tsx` — checkbox `excluir_alergenos` + multi-select de ingredientes alérgenos (`useAllergenIngredients()`). Ambos actualizan `searchParams` al cambiar.
- [x] 3.4 Crear `frontend/src/features/products/components/filters/ActiveFilterChips.tsx` — renderiza un chip por cada filtro activo en la URL con botón "×" individual. Botón "Limpiar todo" elimina todos los filtros.

## 4. Componentes de grilla

- [x] 4.1 Crear `frontend/src/features/products/components/ProductCardSkeleton.tsx` — skeleton loader que imita la forma de `ProductCard` (imagen, dos líneas de texto, botón).
- [x] 4.2 Crear `frontend/src/features/products/components/ProductCard.tsx` — card con imagen (o placeholder SVG), nombre, precio formateado `$ XX.XX`, botón "Agregar". Cuerpo navega a `/cliente/catalogo/:id`. Botón deshabilitado si `!disponible || stock_cantidad === 0` con tooltip "Sin stock". Al agregar exitosamente, muestra feedback "✓ Agregado" por 1 segundo.
- [x] 4.3 Crear `frontend/src/features/products/components/ProductGrid.tsx` — grid responsivo (1→2→3 columnas). Si `isLoading`, renderiza 12 `ProductCardSkeleton`. Si no hay resultados, muestra mensaje "No se encontraron productos con estos filtros."
- [x] 4.4 Crear `frontend/src/features/products/components/Pagination.tsx` — navegación de páginas con botones "Anterior" / "Siguiente" y números de página. Actualiza `page` en `searchParams`.

## 5. Página CatalogPage

- [x] 5.1 Crear `frontend/src/pages/client/CatalogPage.tsx` que compone: `SearchBar`, `CategoryFilter`, `AllergenFilter`, `ActiveFilterChips`, `ProductGrid`, `Pagination`.
- [x] 5.2 En `CatalogPage`, leer todos los filtros desde `useSearchParams` y parsearlos a `ProductFilters` antes de pasarlos a `useProducts(filters)`.
- [x] 5.3 En `CatalogPage`, manejar el caso de `data?.total === 0` mostrando el mensaje vacío a través de `ProductGrid`.

## 6. Página ProductDetailPage

- [x] 6.1 Crear `frontend/src/pages/client/ProductDetailPage.tsx` que use `useParams<{ id: string }>()` para obtener el id y llame `useProduct(Number(id))`.
- [x] 6.2 Implementar la UI del detalle: imagen grande, nombre, descripción (o "Sin descripción"), precio, badge de disponibilidad, chips de categorías, lista de ingredientes con icono de advertencia para alérgenos no-removibles (`AlertTriangle` de lucide-react).
- [x] 6.3 Implementar el selector de cantidad (input `number`, min=1, max=`stock_cantidad`, default=1) y el botón "Agregar al carrito" que llama `useCartStore.getState().addItem(...)` con la cantidad seleccionada.
- [x] 6.4 Implementar el link "← Volver al catálogo" usando `useNavigate()` con `-1` o fallback a `/cliente/catalogo`.
- [x] 6.5 Manejar el estado de error 404: si `useProduct` retorna error con status 404, renderizar el componente `NotFound` o un mensaje inline "Producto no encontrado".

## 7. Routing

- [x] 7.1 En `frontend/src/router/AppRoute.tsx`, reemplazar el `PlaceholderPage` de `catalogo` con `<CatalogPage />`.
- [x] 7.2 En `AppRoute.tsx`, agregar la ruta `catalogo/:id` con elemento `<ProductDetailPage />` dentro del bloque `RoleGuard(['CLIENT'])`.
- [x] 7.3 Importar `CatalogPage` y `ProductDetailPage` en `AppRoute.tsx` con imports directos (no lazy en esta etapa).

## 8. Verificación final

- [x] 8.1 Correr `pnpm --filter frontend lint` y confirmar sin errores.
- [x] 8.2 Verificar que TypeScript no reporta errores (`pnpm --filter frontend tsc --noEmit`).
- [ ] 8.3 Smoke test manual: navegar a `/cliente/catalogo`, verificar que el grid muestra productos, aplicar filtro de categoría, buscar por texto, agregar un producto al carrito y confirmar que el contador del carrito se actualiza.
- [ ] 8.4 Smoke test manual: hacer clic en un producto, verificar que el detalle carga con ingredientes y categorías, seleccionar cantidad 2 y agregar al carrito.
- [ ] 8.5 Smoke test manual: con filtros activos, navegar al detalle y usar el Back del browser — verificar que el catálogo restaura los filtros.
- [ ] 8.6 Verificar responsive: en viewport mobile (375px), el grid muestra 1 columna y los filtros son usables con touch targets ≥44px.
