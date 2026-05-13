## ADDED Requirements

### Requirement: Catalog page with paginated product grid
The system SHALL expose a `CatalogPage` component at route `/cliente/catalogo` that renders a paginated grid of available products fetched from `GET /api/v1/productos`. The page SHALL use `useSearchParams` from React Router to persist filter state in the URL, so that navigating to a product detail and pressing Back restores the exact filter+page combination. The default query SHALL use `disponible=true` (matching backend RN-CA08). Products SHALL be displayed as `ProductCard` components in a responsive grid (1 column on mobile, 2 on `sm:`, 3 on `lg:`). While loading, the grid SHALL render 12 `ProductCardSkeleton` placeholders. The page SHALL use `keepPreviousData: true` so existing cards stay visible while fetching a new page.

#### Scenario: Catalog renders available products on load
- **WHEN** an authenticated CLIENT navigates to `/cliente/catalogo`
- **THEN** the page renders a grid of `ProductCard` components, each with product name, price, image (or placeholder), and an "Agregar" button; only `disponible=true` products are shown

#### Scenario: Skeleton shows on initial load only
- **WHEN** the page is loading for the first time
- **THEN** 12 `ProductCardSkeleton` placeholders are shown instead of cards

#### Scenario: Previous data stays visible during page change
- **WHEN** the user clicks page 2 while on page 1
- **THEN** page 1 cards remain visible until the page 2 response arrives (no blank flash)

#### Scenario: URL reflects active filters
- **WHEN** the user types "pizza" in the search bar and selects category id 3
- **THEN** the URL updates to include `?search=pizza&categoria_id=3` without a full page reload

#### Scenario: Navigating back from detail restores filters
- **WHEN** the user applies filters, clicks a product to open its detail, then presses the browser Back button
- **THEN** the catalog page reloads with the same filters and page number from the URL

### Requirement: Product card component
The system SHALL provide a `ProductCard` component that accepts a `ProductoRead` prop and renders: product image (or a food-placeholder SVG if `imagen_url` is null), product name (`nombre`), price formatted as `$ XX.XX`, and an "Agregar" button. Clicking the card body (excluding the button) SHALL navigate to `/cliente/catalogo/:id`. The "Agregar" button SHALL call `useCartStore.getState().addItem(...)` with `cantidad: 1`. If `disponible === false` OR `stock_cantidad === 0`, the button SHALL be disabled and show a tooltip "Sin stock".

#### Scenario: Clicking the card body navigates to detail
- **WHEN** the user clicks anywhere on the card except the "Agregar" button
- **THEN** the router navigates to `/cliente/catalogo/<product_id>`

#### Scenario: Agregar button adds to cart
- **WHEN** the user clicks "Agregar" on an available product
- **THEN** `useCartStore.getState().addItem({ producto_id, nombre, precio, imagen_url }, 1)` is called AND the button shows a brief "✓ Agregado" feedback for 1 second

#### Scenario: Disabled state when out of stock
- **WHEN** a product has `stock_cantidad === 0` OR `disponible === false`
- **THEN** the "Agregar" button is rendered with `disabled` attribute and shows "Sin stock" on hover/focus

### Requirement: Product detail page
The system SHALL expose a `ProductDetailPage` component at route `/cliente/catalogo/:id` that fetches `GET /api/v1/productos/:id` via `useProduct(id)`. The page SHALL render: product image (large), name, description, price, availability badge, category chips, and an ingredients list that marks non-removable allergens with a warning icon. A quantity selector (default 1, min 1, max `stock_cantidad`) and an "Agregar al carrito" button SHALL be present. Clicking "Agregar al carrito" calls `useCartStore.getState().addItem(...)` with the selected quantity. A "← Volver al catálogo" link SHALL navigate back (`useNavigate(-1)` or to `/cliente/catalogo`).

#### Scenario: Detail page renders full product information
- **WHEN** the user navigates to `/cliente/catalogo/5`
- **THEN** the page renders the product name, description (or "Sin descripción"), price, categories as chips, and the ingredient list with allergen warnings

#### Scenario: Quantity selector respects stock limit
- **WHEN** a product has `stock_cantidad: 3`
- **THEN** the quantity input has `max=3` and the user cannot increment beyond 3

#### Scenario: Agregar al carrito adds selected quantity
- **WHEN** the user sets quantity to 2 and clicks "Agregar al carrito"
- **THEN** `useCartStore.getState().addItem({ producto_id, nombre, precio, imagen_url }, 2)` is called

#### Scenario: Non-removable allergen ingredients are flagged
- **WHEN** the product detail includes an ingredient with `es_alergeno: true` AND `es_removible: false`
- **THEN** that ingredient row displays a warning icon (e.g., `AlertTriangle` from lucide-react) with tooltip "Alérgeno no removible"

#### Scenario: 404 for non-existent product
- **WHEN** the user navigates to `/cliente/catalogo/99999` and the backend returns 404
- **THEN** the page renders the `NotFound` error component or an inline "Producto no encontrado" message

### Requirement: Catalog filter panel with SearchBar, CategoryFilter, AllergenFilter
The system SHALL provide a filter panel composed of three sub-components rendered above the `ProductGrid`:

**SearchBar**: A text input with debounce of 300ms. On change, updates the `search` query param in the URL. Has a clear button when non-empty.

**CategoryFilter**: A `<select>` populated by `useLeafCategories()` (fetches `GET /api/v1/categorias?solo_hojas=true`). Option "Todas las categorías" maps to no `categoria_id` param. Selecting a category updates `categoria_id` in URL and resets page to 1.

**AllergenFilter**: A collapsible panel with (a) a boolean checkbox "Excluir alérgenos" that maps to `excluir_alergenos=true`, and (b) a multi-select list of allergen ingredients from `GET /api/v1/ingredientes?es_alergeno=true` that populates `excluir_alergeno_ids[]`. Both filters are applied with AND semantics (backend-enforced).

**ActiveFilterChips**: Renders one chip per active filter below the panel. Each chip has a × button that removes that individual filter. A "Limpiar todo" button clears all filters at once.

#### Scenario: SearchBar debounces URL update
- **WHEN** the user types "pizza" character by character
- **THEN** the URL `search` param is NOT updated on every keystroke — it updates 300ms after the user stops typing

#### Scenario: CategoryFilter resets page on change
- **WHEN** the user is on page 3 and changes the category filter
- **THEN** the URL updates with the new `categoria_id` AND `page` resets to `1`

#### Scenario: AllergenFilter checkbox updates excluir_alergenos param
- **WHEN** the user checks "Excluir alérgenos"
- **THEN** `excluir_alergenos=true` is added to the URL and the product list refetches

#### Scenario: ActiveFilterChips reflect all active filters
- **WHEN** `search=pizza` and `categoria_id=3` and `excluir_alergenos=true` are in the URL
- **THEN** three chips are rendered: "Búsqueda: pizza ×", "Categoría: <nombre> ×", "Sin alérgenos ×"

#### Scenario: Limpiar todo removes all filter params
- **WHEN** the user clicks "Limpiar todo" with multiple active filters
- **THEN** all filter params are removed from the URL and only `page=1` remains

### Requirement: TanStack Query hooks for product catalog
The system SHALL provide the following hooks in `frontend/src/features/products/hooks/`:

**`useProducts(filters: ProductFilters)`**: wraps `useQuery` with `queryKey: ['products', filters]`, fetches `products.service.getProducts(filters)`, uses `placeholderData: keepPreviousData`.

**`useProduct(id: number)`**: wraps `useQuery` with `queryKey: ['products', id]`, fetches `products.service.getProduct(id)`, `enabled: id > 0`.

**`useLeafCategories()`**: wraps `useQuery` with `queryKey: ['categories', 'leaves']`, fetches `categories.service.getLeafCategories()`, `staleTime: 5 * 60_000`.

#### Scenario: useProducts fetches with current filters
- **WHEN** `useProducts({ page: 2, limit: 20, search: 'pizza' })` is called
- **THEN** a request is issued to `GET /api/v1/productos?page=2&limit=20&search=pizza&disponible=true`

#### Scenario: useProduct is disabled for id=0
- **WHEN** `useProduct(0)` is called (e.g., before the route param is parsed)
- **THEN** no request is dispatched

#### Scenario: useLeafCategories caches for 5 minutes
- **WHEN** `useLeafCategories()` is called from two different components within 5 minutes
- **THEN** only one network request is made; the second call reads from cache
