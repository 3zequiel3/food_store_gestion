## ADDED Requirements

### Requirement: Role-based navigation menu
The system SHALL render a `Navbar` that computes navigation items based on the authenticated user's roles and displays only the items relevant to that role. Unauthenticated users see only public items. (US-075)

#### Scenario: CLIENT sees their menu items
- **WHEN** an authenticated user with role CLIENT views the Navbar
- **THEN** the navigation includes links to: Catálogo (`/products`), Mi Carrito (`/cart`), Mis Pedidos (`/orders`), Mi Perfil (`/profile`), Mis Direcciones (`/addresses`)

#### Scenario: STOCK sees their menu items
- **WHEN** an authenticated user with role STOCK views the Navbar
- **THEN** the navigation includes links to: Productos (`/admin/products`), Categorías (`/admin/categories`), Ingredientes (`/admin/ingredients`)
- **AND** does NOT include links to Pedidos, Usuarios, or Métricas

#### Scenario: PEDIDOS sees their menu item
- **WHEN** an authenticated user with role PEDIDOS views the Navbar
- **THEN** the navigation includes a link to: Panel de Pedidos (`/admin/orders`)
- **AND** does NOT include links to catalog management or users

#### Scenario: ADMIN sees all menu items
- **WHEN** an authenticated user with role ADMIN views the Navbar
- **THEN** the navigation includes all items from CLIENT + STOCK + PEDIDOS roles PLUS: Usuarios (`/admin/users`), Métricas (`/admin/metrics`)

#### Scenario: Unauthenticated user sees public menu
- **WHEN** a user is not authenticated
- **THEN** the Navbar shows only the Catálogo link and the Login/Registrarse buttons; no private links are rendered

### Requirement: Async logout with backend token invalidation
The system SHALL call `authService.logout(refreshToken)` (best-effort) before clearing local auth state when the user clicks the logout button. The UI SHALL respond immediately without waiting for the backend response. (US-004)

#### Scenario: Logout invalidates refresh token in backend
- **WHEN** the user clicks the logout button
- **THEN** `authService.logout` is called with the current `refreshToken` from `useAuthStore`, and `useAuthStore.getState().logout()` is called in the `.finally()` callback

#### Scenario: Logout works even if backend is unreachable
- **WHEN** the user clicks logout and the backend returns an error
- **THEN** the local auth state is cleared regardless and the user is navigated to `/`

### Requirement: Navbar shows authenticated user name
The system SHALL display the authenticated user's `nombre` in the Navbar when logged in, along with a logout button.

#### Scenario: User name is visible when authenticated
- **WHEN** an authenticated user views the Navbar
- **THEN** their `nombre` from `useAuthStore` is displayed alongside the logout button
