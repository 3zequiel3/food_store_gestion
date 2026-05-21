# routing-guards Specification

## Purpose
TBD - created by archiving change setup-frontend-core. Update Purpose after archive.
## Requirements
### Requirement: React Router setup with route definitions
The system SHALL configure react-router-dom v6 with a centralized route configuration defining all application routes.

#### Scenario: Routes are defined centrally
- **WHEN** the application initializes routing
- **THEN** all routes are defined in `frontend/src/app/Router.tsx` with path, component, and access level

#### Scenario: Navigation between pages works
- **WHEN** a user clicks a navigation link
- **THEN** the browser URL updates and the correct page component renders without full page reload

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

### Requirement: Role-based route access
The system SHALL restrict admin routes to users with the ADMIN role, and SHALL restrict the kitchen display route `/cocina` to users with the `COCINA` or `ADMIN` role. The role catalog keeps the four canonical roles (`ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT`) plus the newly added `COCINA`.

#### Scenario: Non-admin user accesses admin route
- **WHEN** a CLIENTE user navigates to `/admin/products`
- **THEN** a 403 Forbidden page is displayed

#### Scenario: Admin user accesses admin route
- **WHEN** an ADMIN user navigates to `/admin/products`
- **THEN** the admin products page renders normally

#### Scenario: COCINA user accesses /cocina
- **WHEN** a user with role `COCINA` navigates to `/cocina`
- **THEN** the kitchen display renders normally

#### Scenario: CLIENT user blocked from /cocina
- **WHEN** a user with only role `CLIENT` navigates to `/cocina`
- **THEN** a 403 Forbidden page is displayed

### Requirement: Error pages
The system SHALL display appropriate error pages for 404 (Not Found) and 403 (Forbidden) scenarios.

#### Scenario: User navigates to non-existent route
- **WHEN** a user navigates to `/this-does-not-exist`
- **THEN** a 404 Not Found page is displayed with a link back to home

#### Scenario: User lacks permission
- **WHEN** a user accesses a route they don't have permission for
- **THEN** a 403 Forbidden page is displayed with explanation

### Requirement: Guards use cookie-backed session state
Route guards SHALL derive local authentication from the user/session state, not token presence.

#### Scenario: User session allows private route
- **WHEN** `authStore.user` is present
- **THEN** private routes render without reading access tokens from localStorage

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

## ADDED Requirements (from change display-cocina-kds)

### Requirement: COCINA login lands on /cocina as exclusive view
The system SHALL redirect a user whose role is `COCINA` to `/cocina` after login, presenting it as the exclusive view for that role without exposing the rest of the application shell.

#### Scenario: COCINA login redirect
- **WHEN** a user with role `COCINA` logs in
- **THEN** they are redirected to `/cocina` and do not see the general navigation

### Requirement: /cocina excluded from inactivity auto-logout
The system SHALL exclude the `/cocina` route from the inactivity auto-logout timer, so the kitchen display stays active during the shift even without user interaction.

#### Scenario: /cocina does not auto-logout on inactivity
- **GIVEN** inactivity auto-logout active for the rest of the app
- **WHEN** the user remains on `/cocina` without interaction past the inactivity threshold
- **THEN** the session is not closed

#### Scenario: Other routes still auto-logout
- **GIVEN** inactivity auto-logout active
- **WHEN** the user remains on a non-`/cocina` route without interaction past the threshold
- **THEN** the session is closed as usual

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

## REMOVED Requirements

### Requirement: React Router setup with route definitions

**Reason**: The previous requirement referenced `frontend/src/app/Router.tsx` (FSD path no longer exists). The current router lives at `frontend/src/router/AppRoute.tsx`. The substantive guard contract is being re-specified.

**Migration**: See `Requirement: Route tree with nested guards` in `openspec/specs/frontend-foundation/spec.md`. Routes are defined in `frontend/src/router/AppRoute.tsx` using a nested tree with `<Outlet />` and guard components (decision D9).

### Requirement: Public route access

**Reason**: Behavior preserved but expressed concretely via the `PublicRoute` guard component.

**Migration**: See `Requirement: Route tree with nested guards` in `frontend-foundation`, scenarios "Unauthenticated user on /login sees the login page" and "Authenticated user on /login redirects to /".

### Requirement: Private route guards

**Reason**: Behavior preserved with the additional contract that the original URL is preserved via `location.state.from` for post-login redirect.

**Migration**: See `Requirement: Route tree with nested guards` in `frontend-foundation`, scenario "Unauthenticated user on /admin redirects to /login with from state".

### Requirement: Role-based route access

**Reason**: Behavior preserved but expressed against the new `RoleGuard` component that reads `useAuthStore.hasRole(...)` and supports multiple allowed roles (`['ADMIN','STOCK','PEDIDOS']` for admin routes).

**Migration**: See `Requirement: Route tree with nested guards` in `frontend-foundation`, scenario "CLIENTE user on /admin sees Forbidden".

### Requirement: Error pages

**Reason**: 404 and 403 were specified; 401 (Unauthorized / sesión expirada) was missing. The new spec adds 401 as a first-class error page so the refresh-failure flow has a destination.

**Migration**: See `Requirement: Error pages for 401, 403, 404` in `frontend-foundation`.

