## 1. Scaffolding del módulo

- [x] 1.1 Crear directorio `backend/features/admin_users/` con `__init__.py`
- [x] 1.2 Crear `backend/features/admin_users/schemas.py` (schemas Pydantic v2 de request y response)
- [x] 1.3 Crear `backend/features/admin_users/repository.py` (AdminUserRepository extendiendo BaseRepository[Usuario])
- [x] 1.4 Crear `backend/features/admin_users/service.py` (AdminUserService usando UoW como context manager)
- [x] 1.5 Crear `backend/features/admin_users/router.py` (APIRouter montado bajo `/admin/usuarios`)
- [x] 1.6 Registrar el router en `backend/main.py` con prefijo `/api/v1`

## 2. Schemas (Pydantic v2)

- [x] 2.1 Definir `AdminUserResponse` — todos los campos públicos: `id`, `email`, `nombre`, `apellido`, `telefono`, `is_active`, `roles: list[str]`, `creado_en`, `actualizado_en`
- [x] 2.2 Definir `AdminUserListResponse` — `items: list[AdminUserResponse]`, `total: int`, `page: int`, `page_size: int`
- [x] 2.3 Definir `AdminUpdateUserRequest` — `nombre`, `apellido`, `telefono` (todos opcionales, `extra="forbid"`)
- [x] 2.4 Definir `AdminChangeRolRequest` — `roles: list[str]` (lista de códigos de rol, al menos 1 elemento)
- [x] 2.5 Definir `AdminChangeEstadoRequest` — `is_active: bool`

## 3. Repository

- [x] 3.1 Implementar `list_paginated(page, page_size, search, rol_codigo)` que retorna `(list[Usuario], int)` — usa `selectinload(Usuario.roles)`, `ilike` para búsqueda, `JOIN user_roles / roles` para filtro de rol
- [x] 3.2 Implementar `find_by_id_with_roles(user_id)` (reutilizar o reimplementar del UserProfileRepository; eager-load roles)
- [x] 3.3 Implementar `count_active_admins_excluding(user_id)` — query que cuenta usuarios activos con rol ADMIN excluyendo el `user_id` dado
- [x] 3.4 Implementar `set_roles(user_id, role_codes)` — elimina todas las filas de `user_roles` para ese usuario e inserta las nuevas dentro de la misma sesión

## 4. Service

- [x] 4.1 Implementar `list_usuarios(page, page_size, search, rol_codigo)` — delega al repo, retorna `(items, total)`
- [x] 4.2 Implementar `update_datos_personales(user_id, payload)` — valida existencia, aplica cambios via `repo.update()`, retorna usuario con roles eager-loaded
- [x] 4.3 Implementar `change_rol(user_id, role_codes)` — valida existencia del usuario, valida códigos de rol contra BD, ejecuta validación de último ADMIN (D4), llama `repo.set_roles()`, revoca refresh tokens via `AuthRepository.revoke_all_user_tokens(user_id)` en la misma UoW
- [x] 4.4 Implementar `change_estado(user_id, is_active)` — aplica `is_active`, si `is_active=False` revoca refresh tokens del usuario en la misma UoW

## 5. Router

- [x] 5.1 Implementar `GET /admin/usuarios` — query params: `page: int = 1`, `page_size: int = 20`, `search: str | None`, `rol: str | None`; `Depends(require_role("ADMIN"))`; retorna `AdminUserListResponse`
- [x] 5.2 Implementar `PUT /admin/usuarios/{id}` — body `AdminUpdateUserRequest`; `Depends(require_role("ADMIN"))`; retorna `AdminUserResponse`; HTTP 404 si no existe
- [x] 5.3 Implementar `PATCH /admin/usuarios/{id}/rol` — body `AdminChangeRolRequest`; `Depends(require_role("ADMIN"))`; retorna `AdminUserResponse`; HTTP 404 si no existe; HTTP 409 si degradaría último ADMIN; HTTP 422 si código de rol inválido
- [x] 5.4 Implementar `PATCH /admin/usuarios/{id}/estado` — body `AdminChangeEstadoRequest`; `Depends(require_role("ADMIN"))`; retorna `AdminUserResponse`

## 6. Tests de integración

- [x] 6.1 Crear `backend/tests/integration/test_admin_users.py` con fixtures de sesión SQLite in-memory y factory de usuarios con roles
- [x] 6.2 Test `GET /admin/usuarios` sin filtros — verifica paginación y estructura de respuesta
- [x] 6.3 Test `GET /admin/usuarios?search=<term>` — verifica que filtra por nombre/email (case-insensitive)
- [x] 6.4 Test `GET /admin/usuarios?rol=STOCK` — verifica filtro por rol
- [x] 6.5 Test `GET /admin/usuarios` con rol CLIENT — espera HTTP 403
- [x] 6.6 Test `PUT /admin/usuarios/{id}` exitoso — verifica datos actualizados en response
- [x] 6.7 Test `PUT /admin/usuarios/{id}` con id inexistente — espera HTTP 404
- [x] 6.8 Test `PUT /admin/usuarios/{id}` con campo `email` en body — espera HTTP 422
- [x] 6.9 Test `PATCH /admin/usuarios/{id}/rol` exitoso — verifica nuevos roles y revocación de refresh tokens
- [x] 6.10 Test `PATCH /admin/usuarios/{id}/rol` quitando último ADMIN — espera HTTP 409
- [x] 6.11 Test `PATCH /admin/usuarios/{id}/rol` con código de rol inválido — espera HTTP 422
- [x] 6.12 Test `PATCH /admin/usuarios/{id}/estado` desactivar — verifica `is_active=false` y revocación de refresh tokens
- [x] 6.13 Test `PATCH /admin/usuarios/{id}/estado` activar usuario desactivado — verifica `is_active=true`
- [x] 6.14 Ejecutar `pytest backend/tests/integration/test_admin_users.py -v` y verificar que todos los tests pasan
