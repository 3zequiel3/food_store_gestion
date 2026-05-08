## Why

El cliente autenticado todavía no puede gestionar su propio perfil: ver sus datos completos (incluido `telefono`), actualizar `nombre`/`apellido`/`telefono` o cambiar su contraseña. `GET /api/v1/auth/me` ya existe pero su `UserResponse` (auth/schemas.py líneas 98-108) **no devuelve `telefono`**, dejando US-061 incumplida; y no hay endpoint alguno para US-062 (editar perfil) ni US-063 (cambiar contraseña). Este change cubre esas tres historias y desbloquea `user-profile-frontend` (Sprint 8). Es el primer change del Sprint 4 (Perfil y Direcciones — Backend) y debe entrar antes de `delivery-addresses-backend` para mantener el orden del roadmap.

## What Changes

- Completar el módulo stub `backend/features/users/` (router con 3 endpoints `not_implemented`, repository/service/schemas vacíos) — **NO** se crea modelo nuevo: `Usuario` ya está en `backend/features/users/models.py`.
- 3 endpoints REST bajo `/api/v1/users` (router ya montado en `backend/main.py:196`):
  - `GET /me` — devuelve perfil completo con `telefono` (resuelve US-061 sin tocar `auth/UserResponse` archivado).
  - `PATCH /me` — edición parcial de `nombre`, `apellido` y/o `telefono` (US-062). `email` y `password_hash` jamás se editan acá.
  - `POST /me/password` — cambio de contraseña con validación de la actual y revocación masiva de refresh tokens (US-063).
- `UserProfileRepository(BaseRepository[Usuario])` con un único método específico `find_by_id_with_roles(user_id)` (eager-load de `roles` para serializar `ProfileResponse` sin lazy-load implícito).
- `UserProfileService` con `get_profile()`, `update_profile()`, `change_password()` — orquesta todo recibiendo `uow: UnitOfWork`. Reusa `verify_password`/`hash_password` de `backend/shared/security.py` y `RefreshTokenRepository.revoke_all_user_tokens()` ya existente en `backend/features/auth/repository.py:39`.
- Schemas Pydantic v2: `ProfileResponse` (incluye `telefono` y `roles[]`, NUNCA `password_hash`), `UpdateProfileRequest` (todos los campos opcionales con `model_dump(exclude_unset=True)`), `ChangePasswordRequest` (`password_actual`, `password_nuevo` con `min_length=8`).
- Spec delta nueva: capability `user-profile` con requirements derivados de US-061, US-062, US-063 + RN-AU01, RN-AU05, RN-RB05.
- Tests de integración cubriendo happy path + edge cases (password actual incorrecta → 401 genérico, password nuevo igual al actual → 422, telefono malformado → 422, sin token → 401, refresh tokens revocados tras cambio).
- **NO** se requiere migración Alembic — la tabla `users` ya existe y no cambia.

## Capabilities

### New Capabilities

- `user-profile`: Endpoints de perfil propio para usuarios autenticados (cualquier rol). Permite leer perfil completo, editar datos personales no-credenciales, y cambiar contraseña con invalidación masiva de refresh tokens. Cubre US-061, US-062, US-063 y aplica RN-AU01 (bcrypt cost ≥ 12), RN-AU05 (replay protection) y RN-RB05 (un usuario solo opera sobre sus propios datos).

### Modified Capabilities

Ninguna. Las capabilities existentes (`auth`, `base-entities`, `error-handling`, `database-migrations`) ya cubren los prerrequisitos sin cambios. **Importante**: NO se modifica la spec archivada `auth` — el endpoint `GET /api/v1/auth/me` queda intacto; el nuevo `GET /api/v1/users/me` lo complementa con un payload más rico.

## Impact

**Code afectado:**
- Modificación: `backend/features/users/{router.py, service.py, repository.py, schemas.py}` — los archivos existen como stub vacío y se completan.
- Modificación menor: `backend/features/users/__init__.py` (exports si aplica — opcional).
- Tests nuevos: `backend/tests/integration/test_user_profile.py`.
- `backend/main.py` ya monta `users_router` en `/api/v1/users` (línea 196) — no requiere cambios.
- No hay migración Alembic.

**Dependencias resueltas (ya archivadas):**
- `auth-backend` ✅ — provee `Depends(get_current_user)`, `Usuario`, `RefreshTokenRepository.revoke_all_user_tokens()`, `hash_password`, `verify_password`.
- `auth-backend-stabilization` ✅ — RFC 7807, exceptions tipadas (`UnauthorizedError`, `BusinessRuleError`, `NotFoundError`).
- `database-migrations` ✅ — tabla `users` con todas sus columnas.
- `base-entities` ✅ — `BaseModel` con `eliminado_en`/`creado_en`/`actualizado_en`.
- `categories-backend`, `ingredients-backend`, `products-backend` ✅ — patrón de `BaseRepository + UoW + service-sin-commit + router-con-commit` ya consolidado y listo para clonar.

**Bloqueado por este change:**
- `user-profile-frontend` (Sprint 8) — necesita los 3 endpoints para implementar la pantalla de "Mi cuenta".
- Indirectamente `delivery-addresses-backend` (#13) reutiliza el patrón users/ módulo, pero no depende del código de este change.

**Historias cubiertas:** US-061, US-062, US-063.

**Estimación:** 2 horas (roadmap docs/CHANGES.md:116). Realista — no hay migración, no hay FSM, modelo ya existe, infraestructura UoW + BaseRepository ya consolidada.

**Decisiones cerradas previo al propose** (registradas en `design.md`):
- Endpoint dedicado `GET /api/v1/users/me` (D1) — NO se toca `auth/UserResponse` archivado.
- `PATCH` (no `PUT`) para edición parcial (D2).
- `apellido` editable junto a `nombre` y `telefono` — coherencia con `RegisterRequest` (D3).
- `POST /me/password` dedicado (D4) — acción, no recurso.
- Revocar **TODOS** los refresh tokens al cambiar password (D5) — US-063 textual + RN-AU05.
- Cualquier rol autenticado puede usar estos endpoints (D8) — `Depends(get_current_user)` directo, sin `require_role`.
- Email **no es editable** en este change (D6) — US-062 textual + spec §3.1 (UQ, identificador). Out of scope.
- `DELETE /users/me` y endpoints admin sobre otros usuarios — out of scope.
