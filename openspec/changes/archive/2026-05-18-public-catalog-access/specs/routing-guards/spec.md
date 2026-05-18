## ADDED Requirements

### Requirement: Public client catalog routes

The system SHALL expose `/cliente/catalogo` and `/cliente/catalogo/:id` as public routes, accessible to unauthenticated visitors. These routes SHALL NOT be wrapped by `PrivateRoute` nor by any `RoleGuard`. They SHALL render inside `AppLayout` (auth-aware) so the chrome (`TopNavbar`, `CartDrawer`) renders consistently for authenticated and anonymous users.

#### Scenario: Anonymous visitor sees catalog list

- **GIVEN** a user is not authenticated
- **WHEN** they navigate to `/cliente/catalogo`
- **THEN** the `CatalogPage` renders with the full product grid, filters, and pagination
- **AND** they are NOT redirected to `/login`
- **AND** the `TopNavbar` shows the public variant (Login / Register CTAs, see `public-navbar`)

#### Scenario: Anonymous visitor sees product detail

- **GIVEN** a user is not authenticated
- **WHEN** they navigate to `/cliente/catalogo/:id` for an existing product
- **THEN** the `ProductDetailPage` renders normally
- **AND** they are NOT redirected to `/login`

#### Scenario: Authenticated client sees the same catalog routes

- **GIVEN** a user is authenticated with role `CLIENT`
- **WHEN** they navigate to `/cliente/catalogo` or `/cliente/catalogo/:id`
- **THEN** the same pages render as for anonymous visitors
- **AND** the `TopNavbar` shows the authenticated variant (cart icon + avatar)

### Requirement: Anonymous-to-checkout auth wall with redirect preservation

The system SHALL redirect anonymous users who attempt to access `/cliente/checkout` to `/login`, preserving the originally requested path so a successful login returns the user to the intended destination. The redirect mechanism SHALL use react-router's `location.state.from` set by `PrivateRoute` and consumed by the `LoginForm` post-success navigation. Successful login SHALL navigate to `state.from` when present, otherwise to `/` as a fallback. Cart contents SHALL be preserved through the entire flow.

#### Scenario: Anonymous user clicks "Iniciar pedido" from cart

- **GIVEN** an anonymous visitor with items in `useCartStore`
- **WHEN** they navigate to `/cliente/checkout` (directly or via the cart drawer CTA)
- **THEN** `PrivateRoute` redirects them to `/login` with `state.from === '/cliente/checkout'`
- **AND** the cart contents in `useCartStore` remain unchanged

#### Scenario: Successful login returns to the saved destination

- **GIVEN** a user is on `/login` with `location.state.from === '/cliente/checkout'`
- **WHEN** the login mutation succeeds
- **THEN** `LoginForm` navigates to `/cliente/checkout` with `replace: true`
- **AND** the user lands on the checkout page with their cart intact

#### Scenario: Login without a saved destination falls back to home

- **GIVEN** a user opens `/login` directly (no `location.state.from`)
- **WHEN** the login mutation succeeds
- **THEN** `LoginForm` navigates to `/` (landing page)

#### Scenario: Anonymous user remains anonymous browsing the catalog

- **GIVEN** an anonymous visitor on `/cliente/catalogo`
- **WHEN** they navigate within the catalog (list ↔ detail) without attempting checkout
- **THEN** no redirect occurs
- **AND** no `state.from` is set

## MODIFIED Requirements

### Requirement: Public route access

The system SHALL allow unauthenticated users to access public routes (home at `/`, login, register, product catalog list at `/cliente/catalogo`, product detail at `/cliente/catalogo/:id`). The home route `/` SHALL NOT be wrapped by any auth guard. The catalog routes `/cliente/catalogo` and `/cliente/catalogo/:id` SHALL NOT be wrapped by `PrivateRoute` nor by `RoleGuard`.

#### Scenario: Unauthenticated user accesses products listing

- **WHEN** an unauthenticated user navigates to `/cliente/catalogo`
- **THEN** the catalog page renders normally without redirect

#### Scenario: Unauthenticated user accesses product detail

- **WHEN** an unauthenticated user navigates to `/cliente/catalogo/:id` for an existing product
- **THEN** the product detail page renders normally without redirect

#### Scenario: Unauthenticated user accesses home page

- **GIVEN** a user is not authenticated
- **WHEN** they visit `/`
- **THEN** they see the full landing page with Hero, Categories, Featured Products, Info, and Footer sections
- **AND** they are NOT redirected to `/login`

#### Scenario: Authenticated user accesses home page

- **GIVEN** a user is authenticated
- **WHEN** they visit `/`
- **THEN** they see the same landing page
- **AND** they are NOT redirected to `/admin` or `/cliente`

#### Scenario: Authenticated user accesses login page

- **WHEN** an authenticated user navigates to `/login`
- **THEN** they are redirected to the home page (no need to log in again)

### Requirement: Private route guards

The system SHALL protect private routes by checking authentication state from authStore before rendering. Private routes SHALL include `/cliente/checkout`, `/cliente/perfil`, `/cliente/direcciones`, `/cliente/pedidos`, `/cliente/pedidos/:id/confirmacion`, and `/admin/*`. The catalog routes (`/cliente/catalogo`, `/cliente/catalogo/:id`) SHALL NOT be wrapped by `PrivateRoute`.

#### Scenario: Unauthenticated user accesses checkout

- **WHEN** an unauthenticated user navigates to `/cliente/checkout`
- **THEN** they are redirected to `/login` with the original URL saved in `location.state.from`

#### Scenario: Unauthenticated user accesses a private client route

- **WHEN** an unauthenticated user navigates to `/cliente/perfil`, `/cliente/direcciones`, or `/cliente/pedidos`
- **THEN** they are redirected to `/login` with the original URL saved in `location.state.from`

#### Scenario: Authenticated user accesses private route

- **WHEN** an authenticated user navigates to `/cliente/checkout`
- **THEN** the checkout page renders normally

#### Scenario: Catalog routes do NOT trigger PrivateRoute

- **WHEN** any user (anonymous or authenticated) navigates to `/cliente/catalogo` or `/cliente/catalogo/:id`
- **THEN** the page renders without the route tree consulting `PrivateRoute`
- **AND** no `state.from` redirect is produced
