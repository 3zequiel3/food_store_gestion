# Spec: sidebar-user-footer

## Purpose
Display authenticated user identity (avatar, name, logout) in the sidebar footer instead of the TopNavbar. Provide clickable navigation to the user's profile page from both desktop sidebar and mobile header.

## Requirements

### Requirement: SidebarFooter displays user identity
The system SHALL render a `SidebarFooter` component at the bottom of the `Sidebar` (desktop, ≥768px) that displays the authenticated user's avatar (initials fallback), display name, and a logout action. The footer SHALL read user data from `useAuthStore`.

#### Scenario: Authenticated user sees identity in sidebar footer
- **GIVEN** a user with `nombre="Juan Perez"` and role `CLIENTE` is authenticated
- **WHEN** the sidebar renders on a viewport ≥768px
- **THEN** the sidebar footer shows "Juan Perez" and an avatar area

#### Scenario: SidebarFooter is absent when unauthenticated
- **GIVEN** no user is authenticated
- **WHEN** the sidebar renders
- **THEN** no `SidebarFooter` is visible

### Requirement: SidebarFooter navigates to profile on click
The system SHALL make the user identity area in `SidebarFooter` clickable, navigating to `/cliente/perfil` for users with `CLIENTE` role and to `/admin/usuarios` for users with `ADMIN`/`STOCK`/`PEDIDOS` roles.

#### Scenario: Client user clicks sidebar footer
- **GIVEN** an authenticated user with role `CLIENTE`
- **WHEN** they click the user identity area in the sidebar footer
- **THEN** the app navigates to `/cliente/perfil`

#### Scenario: Admin user clicks sidebar footer
- **GIVEN** an authenticated user with role `ADMIN`
- **WHEN** they click the user identity area in the sidebar footer
- **THEN** the app navigates to `/admin/usuarios`

### Requirement: SidebarFooter logout action
The system SHALL provide a logout button/icon in `SidebarFooter` that calls `useAuthStore.getState().clearSession()`, clears the query cache, and redirects to `/login`.

#### Scenario: User logs out from sidebar
- **GIVEN** an authenticated user
- **WHEN** they click the logout button in the sidebar footer
- **THEN** the session is cleared, query cache is wiped, and the user is redirected to `/login`

### Requirement: TopNavbar no longer shows user info on desktop
The system SHALL NOT render the user avatar, name, or logout button in `TopNavbar` on viewports ≥768px. The `TopNavbar` SHALL retain the brand/logo and cart button (for clients).

#### Scenario: Desktop TopNavbar has no user info
- **WHEN** the viewport is ≥768px and the user is authenticated
- **THEN** the `TopNavbar` shows only the brand/logo and cart button (if CLIENTE), with no user avatar or name

### Requirement: Mobile TopNavbar user info is clickable to profile
The system SHALL wrap the user identity section in the mobile `TopNavbar` (<768px) in a clickable element (`<button>` or `<Link>`) that navigates to the correct profile route based on role.

#### Scenario: Mobile client taps user info
- **GIVEN** an authenticated user with role `CLIENTE` on a viewport <768px
- **WHEN** they tap the user avatar/name in the TopNavbar
- **THEN** the app navigates to `/cliente/perfil`

#### Scenario: Mobile admin taps user info
- **GIVEN** an authenticated user with role `ADMIN` on a viewport <768px
- **WHEN** they tap the user avatar/name in the TopNavbar
- **THEN** the app navigates to `/admin/usuarios`
