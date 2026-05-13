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
