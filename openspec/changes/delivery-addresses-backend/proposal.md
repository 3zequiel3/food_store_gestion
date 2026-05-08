## Why

El cliente autenticado todavía no puede gestionar sus direcciones de entrega: el módulo `backend/features/addresses/` es un stub con solo `models.py` (definiendo `DireccionEntrega`) y `__init__.py` vacío — no hay router, service, repository ni schemas (verificado con `eza backend/features/addresses/`). La tabla `delivery_addresses` sí existe en la migración inicial (`20260428_0001_8d61b8e48f6b_initial_schema.py:222-254`) y `Pedido` ya tiene FK `direccion_entrega_id` apuntándola (`backend/features/orders/models.py:48-52`), pero **no existen endpoints** para crear, listar, editar, eliminar ni marcar como predeterminada una dirección. Sin estos endpoints, US-024 a US-028 no se cumplen y, lo más importante, **`order-creation-backend` (Sprint 5) está bloqueado**: un pedido necesita una `direccion_entrega_id` válida y propiedad del usuario que lo crea. Este change es el segundo y último del Sprint 4 (Perfil y Direcciones — Backend) y entra después de `user-profile-backend` (ya archivado en `openspec/changes/archive/2026-05-08-user-profile-backend/`).

## What Changes

- Completar el módulo stub `backend/features/addresses/`: crear `repository.py`, `schemas.py`, `service.py`, `router.py` y `README.md`. **NO se crea modelo nuevo**: `DireccionEntrega` ya existe en `backend/features/addresses/models.py:19-50`.
- Agregar el campo `piso_depto: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)` al modelo `DireccionEntrega` (US-024 lista textualmente "piso/depto (opcional)" en línea 977 de `docs/Historias_de_usuario.txt`).
- **Migración Alembic NUEVA y obligatoria** (`backend/alembic/versions/<rev>_add_piso_depto_to_delivery_addresses.py`): agrega la columna `piso_depto VARCHAR(50) NULL` a `delivery_addresses`. Se escribe a mano siguiendo el patrón de `20260508_0001_es_removible_to_product_ingredients.py` — **NO** `--autogenerate` porque Postgres no corre en el ambiente del apply-agent. `down_revision = "es_removible_product_ingredients"` (la head actual).
- 5 endpoints REST bajo `/api/v1/direcciones` (top-level, NO sub-path de `/users/me` — D1):
  - `POST /api/v1/direcciones` — crea dirección, auto-marca `es_principal=True` si es la primera del usuario (US-024, RN-DI01).
  - `GET /api/v1/direcciones` — lista las direcciones del usuario autenticado, sin paginación (US-025, RN-DI03).
  - `PUT /api/v1/direcciones/{id}` — actualización parcial con `model_dump(exclude_unset=True)` y validación de ownership (US-026, RN-DI03).
  - `DELETE /api/v1/direcciones/{id}` — soft delete con validación de ownership; permite borrar la principal y deja al usuario sin predeterminada (US-027, D5).
  - `PATCH /api/v1/direcciones/{id}/predeterminada` — swap atómico: descambia la antigua y marca la nueva (US-028, RN-DI02).
- `AddressRepository(BaseRepository[DireccionEntrega])` con métodos especializados: `find_by_id_and_user(id, user_id)`, `list_active_by_user(user_id)`, `count_active_by_user(user_id)`, `unset_principal_for_user(user_id)`, `find_principal_by_user(user_id)`. CRUD básico heredado sin overrides.
- `AddressService(uow)` con `create()`, `list_for_user()`, `update()`, `delete()`, `set_principal()`. **Service NUNCA hace `uow.commit()`** — el router lo decide.
- Schemas Pydantic v2: `DireccionCreate`, `DireccionUpdate`, `DireccionRead` con `extra="forbid"` en Create/Update (anti-smuggling de `es_principal` y `usuario_id`).
- **Ownership enforcement por 404** (D6): si una dirección no existe o no pertenece al usuario, se responde **404 (NotFoundError)**, NO 403 — evita information leak (patrón Rails). Implementado vía `find_by_id_and_user(id, user_id)` que devuelve `None` en ambos casos.
- Wiring en `backend/main.py`: importar y montar `addresses_router` con prefix `/api/v1/direcciones`, tag `addresses`. Importar router solamente — el modelo ya se registra en línea 61.
- Tests de integración (`backend/tests/integration/test_delivery_addresses.py`) cubriendo happy path, ownership cross-user (404), auto-principal en primera dirección, atomicidad del swap PATCH, anti-smuggling de campos forbidden, soft delete y autenticación faltante.
- Spec delta nueva: capability `delivery-addresses` con requirements derivados de US-024 a US-028 + RN-DI01/DI02/DI03.

## Capabilities

### New Capabilities

- `delivery-addresses`: Endpoints CRUD de direcciones de entrega para clientes autenticados. Permite crear/listar/editar/eliminar direcciones propias y marcar una como predeterminada (atómicamente). Cubre US-024 a US-028 y aplica RN-DI01 (primera dirección auto-principal), RN-DI02 (única predeterminada por usuario), RN-DI03 (ownership por userId del JWT) y RN-RB05 (un cliente solo opera sobre sus propios datos).

### Modified Capabilities

Ninguna. Las capabilities existentes (`auth`, `base-entities`, `error-handling`, `database-migrations`, `user-profile`) ya cubren los prerrequisitos sin cambios. **Importante**: NO se modifica la capability `database-migrations` archivada — la migración nueva de `piso_depto` se agrega como una revision Alembic incremental, no como cambio de spec.

## Impact

**Code afectado:**
- Nuevos: `backend/features/addresses/{router.py, service.py, repository.py, schemas.py, README.md}`.
- Modificación: `backend/features/addresses/models.py` — agregar columna `piso_depto`.
- Nueva migración Alembic: `backend/alembic/versions/<rev>_add_piso_depto_to_delivery_addresses.py` (revision id sugerida: `piso_depto_delivery_addresses`).
- Modificación: `backend/main.py` — importar `addresses_router` y montar con prefix `/api/v1/direcciones`. La línea 61 ya importa los modelos (`from backend.features.addresses import models as _address_models`), no requiere cambios.
- Tests nuevos: `backend/tests/integration/test_delivery_addresses.py`.

**Dependencias resueltas (ya archivadas):**
- `auth-backend` ✅ — provee `Depends(get_current_user)`, `Usuario`, jerarquía RFC 7807.
- `auth-backend-stabilization` ✅ — exceptions tipadas (`NotFoundError`, `BusinessRuleError`, `UnauthorizedError`) y handlers RFC 7807.
- `database-migrations` ✅ — tabla `delivery_addresses` con columnas calle/numero/ciudad/codigo_postal/referencia/es_principal y FK a users.
- `base-entities` ✅ — `BaseModel` con `eliminado_en`/`creado_en`/`actualizado_en`.
- `categories-backend`, `ingredients-backend`, `products-backend` ✅ — patrón `BaseRepository + UoW + service-sin-commit + router-con-commit` consolidado.
- `user-profile-backend` ✅ — patrón self-service con `Depends(get_current_user)` y filtrado por `current_user.id`.
- `fix-base-repository-soft-delete` y `fix-base-repository-immutable-fields` ✅ — `BaseRepository` ya está limpio post-fix; heredar sin overrides defensivos.

**Bloqueado por este change:**
- `delivery-addresses-frontend` (Sprint 8, change #23 en `docs/CHANGES.md:210-213`) — necesita los 5 endpoints para implementar la pantalla "Mis direcciones".
- `order-creation-backend` (Sprint 5, change #14 en `docs/CHANGES.md:129-134`) — un pedido requiere `direccion_entrega_id` válida y propiedad del cliente; sin esta capability no hay direcciones para apuntar.

**Historias cubiertas:** US-024, US-025, US-026, US-027, US-028.

**Estimación:** 3-3.5 horas (vs. 2-3h del roadmap `docs/CHANGES.md:123` — el extra cubre la migración Alembic nueva y los tests de ownership cross-user, no triviales).

**Decisiones cerradas previo al propose** (registradas en `design.md`):
- `D1` — Endpoint base `/api/v1/direcciones` top-level, NO sub-path de `/users/me`.
- `D3` — Auto-marcar la primera dirección como principal en el service usando `count_active_by_user(user_id) == 0`. `es_principal` NO se acepta en `DireccionCreate`.
- `D5` — Borrar la dirección principal está permitido y deja al usuario sin predeterminada. La próxima creación auto-marcará por D3 — sin auto-promoción de otra dirección existente.
- `D6` — Ownership enforcement vía `find_by_id_and_user(id, user_id)`: dirección inexistente o ajena → 404 (no 403), evita information leak.
- `D9` — Agregar columna `piso_depto VARCHAR(50) NULL` con migración Alembic NUEVA escrita a mano (no `--autogenerate`).

**Out of scope (explícito):**
- Validar "sin pedidos activos" antes de DELETE (US-027 lo menciona) → diferido al Sprint 5 cuando exista la tabla `orders` con datos.
- Geocoding / coordenadas lat-lng — no está en US-024 a US-028.
- Validación específica de código postal argentino — permisivo, `String(20)` con `min_length`/`max_length` razonables.
- Endpoint admin sobre direcciones de cualquier usuario — fuera del Sprint 4.
- `zona_entrega` o restricciones geográficas — fuera del Sprint 4.
- Auto-promoción de otra dirección al borrar la principal — D5 explícito: deja sin principal.
- `GET /api/v1/direcciones/{id}` individual — ninguna US lo requiere; el frontend usa el listado.
