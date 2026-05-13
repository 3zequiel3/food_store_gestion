## Why

La ruta `/admin/usuarios` tiene un `PlaceholderPage`. El backend está completamente implementado con 4 endpoints: listado paginado con filtros (`GET /admin/usuarios`), edición de datos personales (`PUT /{id}`), cambio de roles (`PATCH /{id}/rol`) y activar/desactivar cuenta (`PATCH /{id}/estado`). Este change construye la UI de administración de usuarios.

## What Changes

- Feature folder `features/admin-users/` con tipos, service y hooks para los 4 endpoints.
- Componentes: `UserStatusBadge`, `RoleBadge`, `EditUserModal`, `ChangeRolModal`, `ToggleEstadoModal`, `AdminUserRow`, `AdminUsersTable`.
- Página `AdminUsersPage` en `/admin/usuarios`: tabla paginada con filtros de búsqueda por nombre/email y por rol, con acciones por fila (3 modales).
- `AppRoute.tsx` reemplaza `PlaceholderPage` de `/admin/usuarios` → `AdminUsersPage`.

## Capabilities

### New Capabilities
- `admin-users-frontend`: UI para gestión de usuarios desde el panel de administración.

### Modified Capabilities
- (ninguna — los endpoints del backend no cambian)

## Impact

- **Nuevos archivos**: `features/admin-users/types/`, `features/admin-users/services/`, `features/admin-users/hooks/`, `features/admin-users/components/`, `pages/admin/AdminUsersPage.tsx`
- **Modificados**: `router/AppRoute.tsx` (reemplaza PlaceholderPage en `/admin/usuarios`)
- **APIs consumidas**: `GET /api/v1/admin/usuarios`, `PUT /api/v1/admin/usuarios/:id`, `PATCH /api/v1/admin/usuarios/:id/rol`, `PATCH /api/v1/admin/usuarios/:id/estado`
- **Rol requerido**: Solo ADMIN (backend ya lo valida, frontend lo tiene por RoleGuard)
