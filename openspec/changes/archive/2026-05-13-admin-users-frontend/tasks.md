## 1. Feature folder — tipos, service y hooks

- [x] 1.1 Crear `frontend/src/features/admin-users/types/admin-users.types.ts` con `AdminUserResponse`, `AdminUserListResponse`, `AdminUpdateUserRequest`, `AdminChangeRolRequest`, `AdminChangeEstadoRequest`
- [x] 1.2 Crear `frontend/src/features/admin-users/services/admin-users.service.ts` con `listUsers`, `updateUser`, `changeRol`, `changeEstado`
- [x] 1.3 Crear `frontend/src/features/admin-users/hooks/useAdminUsers.ts` — query paginada con `{ page, search?, rol? }`, `staleTime: 30_000`
- [x] 1.4 Crear `frontend/src/features/admin-users/hooks/useUpdateUser.ts` — mutation PUT, `onSuccess` invalida `['admin-users']` y muestra toast
- [x] 1.5 Crear `frontend/src/features/admin-users/hooks/useChangeRol.ts` — mutation PATCH /rol, maneja 409 con toast de error específico
- [x] 1.6 Crear `frontend/src/features/admin-users/hooks/useChangeEstado.ts` — mutation PATCH /estado, `onSuccess` invalida `['admin-users']` y muestra toast

## 2. Componentes de tabla y badges

- [x] 2.1 Crear `frontend/src/features/admin-users/components/UserStatusBadge.tsx` — badge activo/inactivo con color
- [x] 2.2 Crear `frontend/src/features/admin-users/components/RoleBadge.tsx` — badge por rol (CLIENT/ADMIN/STOCK/PEDIDOS) con color distintivo
- [x] 2.3 Crear `frontend/src/features/admin-users/components/AdminUserRow.tsx` — fila de tabla con datos del usuario y botones de acción (editar, cambiar rol, toggle estado)
- [x] 2.4 Crear `frontend/src/features/admin-users/components/AdminUserFilters.tsx` — input de búsqueda + select de rol, refleja y actualiza URL params

## 3. Modales de acción

- [x] 3.1 Crear `frontend/src/features/admin-users/components/EditUserModal.tsx` — formulario nombre/apellido/telefono, validación inline, usa `useUpdateUser`
- [x] 3.2 Crear `frontend/src/features/admin-users/components/ChangeRolModal.tsx` — checkboxes CLIENT/ADMIN/STOCK/PEDIDOS, submit deshabilitado si ninguno marcado, usa `useChangeRol`
- [x] 3.3 Crear `frontend/src/features/admin-users/components/ToggleEstadoModal.tsx` — confirmación explícita con nombre del usuario y efecto esperado, usa `useChangeEstado`

## 4. Página y ruta

- [x] 4.1 Crear `frontend/src/pages/admin/AdminUsersPage.tsx` — tabla con `AdminUserRow`, `AdminUserFilters`, paginación, skeleton, estado vacío; gestiona `selectedUser` y qué modal está abierto
- [x] 4.2 Reemplazar `PlaceholderPage` de `/admin/usuarios` → `AdminUsersPage` en `AppRoute.tsx`
