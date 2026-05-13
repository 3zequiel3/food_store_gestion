## MODIFIED Requirements

### Requirement: Route tree with nested guards
The system SHALL configure `frontend/src/router/AppRoute.tsx` as a nested route tree where guard components (`PublicRoute`, `PrivateRoute`, `RoleGuard`) wrap parent routes and child routes render inside `<Outlet />`. `PublicRoute` SHALL redirect authenticated users to `/`. `PrivateRoute` SHALL redirect unauthenticated users to `/login` and preserve the original URL via `location.state.from`. `RoleGuard` SHALL check `useAuthStore.hasRole(...)` against the `roles` prop and redirect to `/403` if denied.

Inside the `RoleGuard(['CLIENT'])` block, the routes SHALL be:
- `/cliente/catalogo` → `CatalogPage` (replaces the previous `PlaceholderPage`)
- `/cliente/catalogo/:id` → `ProductDetailPage` (new route)
- `/cliente/pedidos` → `PlaceholderPage` (unchanged)
- `/cliente/direcciones` → `PlaceholderPage` (unchanged)
- `/cliente/perfil` → `PlaceholderPage` (unchanged)

#### Scenario: Unauthenticated user on /login sees the login page
- **WHEN** an unauthenticated user navigates to `/login`
- **THEN** `PublicRoute` allows render and `LoginPage` is shown

#### Scenario: Authenticated user on /login redirects to /
- **WHEN** an authenticated user navigates to `/login`
- **THEN** `PublicRoute` redirects to `/`

#### Scenario: Unauthenticated user on /admin redirects to /login with from state
- **WHEN** an unauthenticated user navigates to `/admin/usuarios`
- **THEN** `PrivateRoute` redirects to `/login` and `location.state.from === '/admin/usuarios'`

#### Scenario: CLIENTE user on /admin sees Forbidden
- **WHEN** a user with role `CLIENTE` (no `ADMIN`/`STOCK`/`PEDIDOS`) navigates to `/admin/usuarios`
- **THEN** `RoleGuard` redirects to `/403`

#### Scenario: Unknown path renders NotFound
- **WHEN** any user navigates to `/this-does-not-exist`
- **THEN** the `NotFound` page (404) is rendered

#### Scenario: /cliente/catalogo renders CatalogPage
- **WHEN** an authenticated CLIENT navigates to `/cliente/catalogo`
- **THEN** `CatalogPage` is rendered (NOT a PlaceholderPage)

#### Scenario: /cliente/catalogo/:id renders ProductDetailPage
- **WHEN** an authenticated CLIENT navigates to `/cliente/catalogo/5`
- **THEN** `ProductDetailPage` is rendered with route param `id = "5"`
