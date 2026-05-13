## Context

El backend ya tiene autenticación y autorización completas (`auth-backend` ✅). Los roles fijos (ADMIN=1, STOCK=2, PEDIDOS=3, CLIENT=4) viven en la tabla `roles`. El modelo `Usuario` tiene `is_active` y soft-delete via `eliminado_en`. La relación M:N `user_roles` conecta usuarios y roles.

El módulo `backend/features/users/` es exclusivamente self-service: opera sobre `current_user.id` sin exponer el `user_id` como parámetro de ruta (RN-RB05). No se puede extender ese router para operaciones admin sin violar esa garantía de diseño.

## Goals / Non-Goals

**Goals:**
- Listado paginado de usuarios con filtros de búsqueda (email/nombre) y filtro por rol.
- Edición de datos personales de cualquier usuario (nombre, apellido, teléfono).
- Reemplazo atómico del conjunto de roles de un usuario.
- Activación/desactivación de usuarios con invalidación de refresh tokens.
- Validación de invariante de negocio: el sistema siempre tiene al menos un ADMIN activo (RN-RB04).
- Cobertura de integración con pytest + SQLite in-memory.

**Non-Goals:**
- Eliminación física de usuarios (soft delete ya existe; no se expone vía admin).
- Creación de usuarios desde admin (el registro ya existe en `auth-backend`).
- Cambio de email o contraseña de otro usuario desde admin (fuera del spec US-053–055).
- Frontend admin (sprint 12, change `admin-users-frontend`).

## Decisions

### D1 — Nuevo feature `admin_users`, no extender `users`

**Decisión**: crear `backend/features/admin_users/` con router, schemas, service y repository propios. El router self-service `/api/v1/usuarios` permanece intacto.

**Alternativa descartada**: agregar endpoints admin dentro de `backend/features/users/router.py` con una rama condicional sobre el rol.

**Justificación**: el router de `users` tiene una garantía explícita de que nunca expone `user_id` como path param (RN-RB05). Mezclar endpoints admin en ese módulo viola esa garantía conceptual y añade complejidad de permisos en un router que se define a sí mismo como self-service. Un módulo separado mantiene separación de responsabilidades limpia.

### D2 — Prefijo de ruta `/api/v1/admin/usuarios`

**Decisión**: todos los endpoints de este change se montan bajo `/api/v1/admin/usuarios`.

**Alternativa descartada**: `/api/v1/usuarios` con distinción por rol.

**Justificación**: la spec de US-053 dice `GET /api/admin/usuarios`. El prefijo `/admin/` es el contrato del integrador para la UI del Sprint 12. Mantener el prefijo separado facilita aplicar un middleware de autorización global por prefijo en el futuro (aunque por ahora se aplica por endpoint con `require_role`).

### D3 — PATCH /estado reemplaza soft delete para desactivación

**Decisión**: desactivar un usuario significa `is_active = False`, NO `eliminado_en = now()`.

**Justificación**: US-055 exige "los pedidos históricos se mantienen intactos" y el criterio de aceptación dice "no puede loguearse más". `is_active = False` hace exactamente eso: `get_current_user` ya filtra `is_active = True`. El soft delete (`eliminado_en`) está reservado para eliminación definitiva de datos, que no forma parte del scope.

### D4 — Validación de "último ADMIN" en la capa de servicio

**Decisión**: antes de remover el rol ADMIN de un usuario, el service cuenta usuarios activos con rol ADMIN excluyendo al target. Si el resultado es 0, lanza `ConflictError` (HTTP 409).

**Query**: `SELECT COUNT(*) FROM users JOIN user_roles ON ... JOIN roles ON ... WHERE roles.codigo = 'ADMIN' AND users.is_active = true AND users.eliminado_en IS NULL AND users.id != :target_id`.

**Justificación**: es una regla de negocio (RN-RB04), pertenece al service, no al router. El repositorio expone un método `count_active_admins_excluding(user_id)` para mantener la query en el repo layer.

### D5 — Cambio de rol invalida refresh tokens del usuario

**Decisión**: al ejecutar `PATCH /rol`, después de actualizar `user_roles`, el service llama `AuthRepository.revoke_all_user_tokens(user_id)` dentro de la misma UoW.

**Justificación**: US-054 dice "el próximo token que obtenga ese usuario tendrá el nuevo rol". Los access tokens en circulación son de corta vida (~30min, RN-AU02) y no se pueden invalidar sin una blocklist. Revocar los refresh tokens es la garantía práctica: al expirar el access token, el usuario debe hacer login nuevamente y obtendrá un token con los roles actualizados.

### D6 — AdminUserRepository extiende BaseRepository, comparte sesión con AuthRepository vía UoW

**Decisión**: el service recibe la UoW como context manager. Dentro de un mismo `with uow:` puede instanciar tanto `AdminUserRepository(uow.session)` como `AuthRepository(uow.session)`, garantizando atomicidad en operaciones multi-tabla (rol + revocación de tokens).

**Justificación**: patrón establecido en el proyecto desde `refactor-uow-to-context-manager` ✅.

### D7 — Paginación y filtros en el repositorio

**Decisión**: `AdminUserRepository.list_paginated(page, page_size, search, rol_codigo)` construye la query en el repo layer con `ilike` para búsqueda y `JOIN roles` para filtro de rol. Retorna `(items: list[Usuario], total: int)` en una sola llamada al repo (count + select).

**Alternativa descartada**: paginación en el service (dos llamadas separadas al repo).

**Justificación**: reduce roundtrips de sesión. El repo tiene acceso a la sesión para ejecutar ambas queries dentro del mismo contexto de transacción.

### D8 — `PUT /admin/usuarios/{id}` edita solo datos personales, no rol ni estado

**Decisión**: el schema `AdminUpdateUserRequest` acepta `nombre`, `apellido`, `telefono`. Rol y estado tienen endpoints dedicados (`PATCH /rol`, `PATCH /estado`).

**Justificación**: operaciones con efectos secundarios distintos (invalidación de tokens, validación de último ADMIN) merecen endpoints separados para claridad semántica y para que los tests puedan ejercitar cada invariante de forma independiente.

## Risks / Trade-offs

**[Riesgo]** Concurrencia: dos requests simultáneos podrían pasar la validación "último ADMIN" al mismo tiempo, resultando en un sistema sin admins.
→ **Mitigación**: el count se hace dentro de la misma transacción que hace el UPDATE. Con el nivel de aislamiento por defecto de Postgres (READ COMMITTED) hay una ventana pequeña. Para el alcance académico esto es aceptable; en producción se usaría un SELECT FOR UPDATE o una constraint a nivel de BD.

**[Riesgo]** El test de integración usa SQLite in-memory que no soporta todas las features de Postgres.
→ **Mitigación**: las queries usadas (`ilike`, `join`, `count`) son compatibles con SQLite. No se usan CTEs ni arrays.

**[Trade-off]** No se invalidan los access tokens al cambiar rol/estado.
→ **Aceptado**: ciclo de vida de access token corto (30min). Para el scope académico es suficiente. Documentado en el response del endpoint.

## Open Questions

(ninguna — todas las decisiones están cerradas en base a la spec y las reglas de negocio existentes)
