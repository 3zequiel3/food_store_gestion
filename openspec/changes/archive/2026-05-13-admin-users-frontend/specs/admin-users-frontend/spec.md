## ADDED Requirements

### Requirement: AdminUsersPage displays paginated user list
The system SHALL provide an `AdminUsersPage` at `/admin/usuarios` that displays all users (active and inactive) in a paginated table. Each row SHALL show: email, nombre + apellido, roles (as badges), is_active status, and action buttons.

#### Scenario: Page loads with user list
- **WHEN** an ADMIN navigates to `/admin/usuarios`
- **THEN** the page SHALL fetch `GET /api/v1/admin/usuarios` and render a table with one row per user

#### Scenario: Empty state
- **WHEN** the API returns zero users matching the current filters
- **THEN** the page SHALL display an empty state message

#### Scenario: Loading state
- **WHEN** the API request is in flight
- **THEN** the page SHALL display skeleton rows in place of the table content

### Requirement: AdminUsersPage supports search and role filter
The system SHALL support filtering the user list by search term (nombre/email) and by role code. Filters SHALL be reflected in URL query params and SHALL reset pagination to page 1 on change.

#### Scenario: Search by name or email
- **WHEN** the admin types in the search input
- **THEN** the table SHALL refetch with the `search` query param and display matching users

#### Scenario: Filter by role
- **WHEN** the admin selects a role from the role filter dropdown
- **THEN** the table SHALL refetch with the `rol` query param and display only users with that role

#### Scenario: Filter reset resets to page 1
- **WHEN** the admin changes any filter while on page 3
- **THEN** the pagination SHALL reset to page 1

### Requirement: Edit user personal data modal
The system SHALL provide an `EditUserModal` that allows editing `nombre`, `apellido`, and `telefono` of a user via `PUT /api/v1/admin/usuarios/:id`.

#### Scenario: Successful edit
- **WHEN** admin submits the edit form with valid data
- **THEN** the system SHALL call `PUT /admin/usuarios/:id`, show a success toast, close the modal, and refresh the user list

#### Scenario: Validation error
- **WHEN** admin submits with `nombre` or `apellido` shorter than 2 characters
- **THEN** the modal SHALL display inline validation errors and SHALL NOT submit

### Requirement: Change user roles modal
The system SHALL provide a `ChangeRolModal` that allows replacing the full role set of a user via `PATCH /api/v1/admin/usuarios/:id/rol`. Roles SHALL be presented as checkboxes: CLIENT, ADMIN, STOCK, PEDIDOS. At least one role SHALL be selected.

#### Scenario: Successful role change
- **WHEN** admin selects new roles and confirms
- **THEN** the system SHALL call `PATCH /admin/usuarios/:id/rol`, show a success toast, close the modal, and refresh the user list

#### Scenario: Last ADMIN protection
- **WHEN** backend returns HTTP 409 (last admin)
- **THEN** the modal SHALL stay open and display an error message explaining the constraint

#### Scenario: No roles selected
- **WHEN** admin deselects all checkboxes
- **THEN** the submit button SHALL be disabled

### Requirement: Toggle user account state modal
The system SHALL provide a `ToggleEstadoModal` that activates or deactivates a user account via `PATCH /api/v1/admin/usuarios/:id/estado`. The modal SHALL require explicit confirmation before executing the action.

#### Scenario: Deactivate user
- **WHEN** admin confirms deactivation of an active user
- **THEN** the system SHALL call `PATCH /admin/usuarios/:id/estado` with `{ is_active: false }`, show a success toast, close the modal, and refresh the user list

#### Scenario: Activate user
- **WHEN** admin confirms activation of an inactive user
- **THEN** the system SHALL call `PATCH /admin/usuarios/:id/estado` with `{ is_active: true }`, show a success toast, close the modal, and refresh the user list

### Requirement: Admin users feature folder
The system SHALL have a `features/admin-users/` folder containing:
- `types/admin-users.types.ts` — mirrors `AdminUserResponse`, `AdminUserListResponse`, `AdminUpdateUserRequest`, `AdminChangeRolRequest`, `AdminChangeEstadoRequest`
- `services/admin-users.service.ts` — wraps all 4 endpoints
- `hooks/useAdminUsers.ts` — paginated query with filters
- `hooks/useUpdateUser.ts` — mutation for PUT
- `hooks/useChangeRol.ts` — mutation for PATCH /rol
- `hooks/useChangeEstado.ts` — mutation for PATCH /estado

#### Scenario: All mutations invalidate the user list cache
- **WHEN** any mutation (update, changeRol, changeEstado) succeeds
- **THEN** `['admin-users']` query cache SHALL be invalidated
