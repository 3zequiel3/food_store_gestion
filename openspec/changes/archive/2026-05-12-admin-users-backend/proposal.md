## Why

El sistema no expone ningún endpoint que permita al ADMIN gestionar los usuarios registrados: ver su estado, editar sus datos personales, cambiar sus roles o desactivarlos. Sin esta capacidad, la administración del sistema requiere intervención directa en la base de datos (US-053, US-054, US-055).

## What Changes

- **Nuevo router** `GET /api/v1/admin/usuarios` — listado paginado con búsqueda por email/nombre y filtro por rol.
- **Nuevo endpoint** `PUT /api/v1/admin/usuarios/{id}` — editar datos personales (nombre, apellido, teléfono) de cualquier usuario.
- **Nuevo endpoint** `PATCH /api/v1/admin/usuarios/{id}/rol` — asignar/reemplazar el conjunto de roles de un usuario; incluye validación de no quitar el último ADMIN del sistema (RN-RB04).
- **Nuevo endpoint** `PATCH /api/v1/admin/usuarios/{id}/estado` — activar o desactivar un usuario (`is_active`); invalida refresh tokens del usuario al desactivarlo (US-055).
- **Nuevo feature** `backend/features/admin_users/` — router, schemas, service, repository propios para este dominio; NO se extiende el router self-service de `/api/v1/usuarios`.
- Todos los endpoints requieren `Depends(require_role("ADMIN"))`.
- La invalidación de refresh tokens al cambiar rol/estado reutiliza la lógica ya presente en `AuthService`.

## Capabilities

### New Capabilities

- `admin-users`: Gestión administrativa de usuarios — listado paginado con filtros, edición de datos personales, cambio de roles, activación/desactivación, validación de último ADMIN.

### Modified Capabilities

(ninguna — los endpoints self-service de `/api/v1/usuarios` no cambian)

## Impact

- **Nuevo código**: `backend/features/admin_users/` (router, schemas, service, repository).
- **API**: 4 nuevos endpoints bajo `/api/v1/admin/usuarios`.
- **Reutilización**: `BaseRepository[Usuario]`, `UserProfileRepository.find_by_id_with_roles`, lógica de invalidación de refresh tokens de `AuthService`.
- **Sin migraciones**: No se agregan ni modifican columnas — el campo `is_active` ya existe en `users`.
- **Tests**: `backend/tests/integration/test_admin_users.py` — cobertura de todos los endpoints, incluyendo los casos de borde del último ADMIN.
- **Dependencias del roadmap**: requiere `auth-backend` ✅ (archivado Sprint 1).
