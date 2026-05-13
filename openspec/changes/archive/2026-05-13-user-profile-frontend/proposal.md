## Why

El catálogo (Sprint 7) está operativo, pero los clientes no tienen forma de ver ni editar sus datos personales ni cambiar su contraseña. Los tres endpoints del backend (`GET`, `PATCH /usuarios/me` y `POST /usuarios/me/password`) están en producción desde Sprint 4 — solo falta la UI que los consuma.

## What Changes

- Reemplazar el `PlaceholderPage` de `/cliente/perfil` con `ProfilePage` real.
- Formulario inline de datos personales: nombre, apellido, teléfono — con TanStack Form + Zod y validación onBlur. Éxito → actualiza `authStore.user` y muestra toast/confirmación inline.
- Modal de cambio de contraseña: contraseña actual + nueva (mín. 8 caracteres). POST 204 → `clearSession()` + redirect a `/login` (el backend revocó todos los refresh tokens).
- Nuevo servicio `user-profile.service.ts` que expone `getProfile()`, `updateProfile()`, `changePassword()` contra `ENDPOINTS.usuarios.*`.
- Nuevos hooks TanStack Query: `useProfile()`, `useUpdateProfile()` (mutation), `useChangePassword()` (mutation).
- Nuevo tipo `ProfileRead` con los campos extra que el endpoint `/usuarios/me` devuelve y que `Usuario` de authStore no tiene: `telefono`, `actualizado_en`.

## Capabilities

### New Capabilities
- `user-profile-frontend`: UI cliente para visualizar y editar perfil propio y cambiar contraseña.

### Modified Capabilities
<!-- ninguna spec de backend cambia -->

## Impact

- **Archivos nuevos**: `features/user-profile/` (service, types, hooks, schemas, components, page).
- **Archivos modificados**: `router/AppRoute.tsx` (reemplazar PlaceholderPage en `/cliente/perfil`).
- **authStore**: se actualiza `user` en memoria tras PATCH exitoso (no afecta la interfaz del store).
- **Sin cambios de backend**: todos los endpoints ya existen y están testeados.
- **Dependencias externas**: ninguna nueva — TanStack Form/Query, Zod y apiClient ya están presentes.
