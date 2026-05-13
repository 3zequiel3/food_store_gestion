# Proposal: refactor-auth-to-uow

## Why

`refactor-uow-to-context-manager` (archivado 2026-05-11) migró los 5 features de dominio (categories, ingredients, products, users, addresses) al patrón **service-driven UoW**: el service abre `with UnitOfWork() as uow:`, ejecuta la lógica, y `__exit__` hace commit/rollback. Auth quedó FUERA del scope como deuda técnica explícita (D6 diferido en el design archivado) porque usa `Session` directa via `Depends(get_db)` — un patrón distinto.

Hoy auth es el **único feature del backend** que sigue el patrón viejo. El precio:

- **Inconsistencia arquitectónica**: 5 features con `service.method() // commit en __exit__`, 1 feature (auth) con `Depends(get_db) // commit implícito en yield`.
- **Bug latente de atomicidad en `register`**: el flujo actual es `service.register(data)` (crea Usuario + UsuarioRol con `flush()`, sin commit) → router llama `service._create_token_pair(user)` (crea RefreshToken con `flush()`) → `get_db()` hace UN solo commit al salir del yield. **El commit es correcto en práctica** pero depende de magia implícita: si `_create_token_pair` falla, el rollback de `get_db` revierte todo. **Pero la responsabilidad transaccional vive en el adapter HTTP, no en el caso de uso**. Con UoW explícito el invariante es legible.
- **`async def` sin `await`**: `AuthService` declara métodos `async def` que no contienen ningún `await` real (SQLAlchemy sync). Es overhead semántico sin beneficio — confunde a quien lee el código creyendo que hay I/O async.
- **`get_db()` huérfano**: post-refactor el único consumidor de `get_db()` es auth (router + dependencies + tests). Eliminándolo del contrato público se cierra la deuda técnica completa del UoW.
- **5 endpoints de auth + 22 endpoints downstream** (categories, products, ingredients, addresses, users) dependen de `get_current_user` y `require_role`. Cualquier inconsistencia en el lifecycle de sesión de auth afecta a TODO el backend autenticado.

Este change cierra la deuda: migra auth al mismo patrón service-driven UoW, corrige el bug latente de `register` (que pasa a retornar `TokenPairResponse` directamente en una transacción atómica), convierte el service a `sync`, y elimina `get_db()` del contrato público.

> **Continuidad arquitectónica con la spec del integrador §7.1.** La spec canónica dice "router abre UoW". El refactor anterior se desvió justificadamente para adoptar el patrón puro de clean architecture (service abre UoW). Este change preserva esa decisión heredada por consistencia con los 5 features ya migrados.

## What Changes

### Estructura del AuthService

- **MODIFIED**: `AuthService.__init__(self)` — sin argumentos. Pierde `session: Session` y `self.refresh_token_repo` como atributos de instancia.
- **MODIFIED**: Cada método público abre `with UnitOfWork() as uow:`. Los repos (`RefreshTokenRepository`) se construyen dentro del bloque con `uow.session`.
- **MODIFIED**: Los métodos `async def` pasan a `def` (sync). El service no tiene I/O async real.
- **MODIFIED (BREAKING en interfaz interna)**: `register()` cambia firma — retorna `TokenPairResponse` directamente en lugar de `Usuario`. Cierra el bug latente de atomicidad: Usuario + UsuarioRol + RefreshToken se persisten en una única transacción explícita.
- **MODIFIED**: `_create_token_pair` se mantiene como helper privado pero acepta `session` explícita; cada caller lo invoca DENTRO del mismo `with UnitOfWork()` y pasa `uow.session`.

### Auth dependencies (excepción D1 al patrón general)

- **MODIFIED**: `get_current_user` y `get_optional_user` dejan de usar `Depends(get_db)`. Abren una **sesión read-only directa** (vía `get_session_factory()()`) en lugar de un `UnitOfWork` completo. Justificación: ambas son lecturas puras (1 SELECT), middleware HTTP, no operaciones de negocio. UoW completo es overhead innecesario.

### Eliminación de get_db()

- **REMOVED**: `get_db()` desaparece del contrato público de `backend/shared/database.py`. La función queda sin consumidores reales en producción tras el refactor.
- **REMOVED**: `override_get_db` de `backend/tests/conftest.py` desaparece. El monkeypatch existente de `get_session_factory` (heredado del refactor anterior) cubre auth dependencies en tests.

### Router cleanup

- **MODIFIED**: 5 endpoints de auth (`register`, `login`, `refresh`, `logout`, `get_me`) eliminan `db=Depends(get_db)` de sus firmas. Eliminan import de `get_db`.
- **MODIFIED**: `register` deja de orquestar dos llamadas al service (`service.register(data)` + `service._create_token_pair(user)`); pasa a una sola llamada `service.register(data)` que ya retorna `TokenPairResponse`.

### Documentation cleanup

- **MODIFIED**: docstring de `get_db` en `backend/shared/database.py` (líneas 90-119) hoy menciona `get_uow` que fue eliminado en el refactor anterior. Se elimina junto con la función.
- **MODIFIED**: `backend/dependencies.py` línea 4 menciona "use from backend.shared.database import get_db" — queda obsoleto, se actualiza o elimina.

## Capabilities

### New Capabilities

(Ninguna nueva — refactor estructural con corrección de invariante de atomicidad)

### Modified Capabilities

- `auth`: agregar requirement explícito sobre la atomicidad transaccional de `register` (Usuario + UsuarioRol + RefreshToken se persisten como una sola unidad). Hoy la spec habla de comportamiento HTTP y reglas de negocio (RN-AU01 a RN-AU08) pero no menciona la propiedad transaccional. Esta delta hace explícito el invariante que el refactor garantiza. **Ningún requirement existente cambia** — el contrato HTTP se mantiene idéntico.

## Impact

### Código de producción afectado (5 archivos)

| Archivo | Cambio |
|---|---|
| `backend/features/auth/service.py` | `__init__(self)` sin args; métodos sync; cada método abre `with UnitOfWork() as uow:`; `register` retorna `TokenPairResponse` |
| `backend/features/auth/router.py` | 5 endpoints sin `Depends(get_db)`; `register` con una sola llamada al service; sin import de `get_db` |
| `backend/features/auth/dependencies.py` | `get_current_user` y `get_optional_user` con sesión directa; sin `Depends(get_db)` |
| `backend/shared/database.py` | Eliminar `get_db()` y su docstring obsoleto |
| `backend/dependencies.py` | Actualizar/eliminar comentario obsoleto sobre `get_db` |

### Test infrastructure afectado (1 archivo)

| Archivo | Cambio |
|---|---|
| `backend/tests/conftest.py` | Eliminar `override_get_db` y `app.dependency_overrides[get_db] = ...`. El monkeypatch existente de `get_session_factory` cubre el nuevo flujo. |

### Conteo mecánico (verificado con `rg`)

- 8 ocurrencias de `Depends(get_db)` eliminadas (5 en router, 2 en dependencies, 1 en conftest).
- 5 ocurrencias de `async def` → `def` en `AuthService` (`register`, `login`, `refresh`, `logout`, `_create_token_pair`).
- 1 función `get_db()` eliminada de `backend/shared/database.py`.
- 1 cambio de firma: `register() -> Usuario` pasa a `register() -> TokenPairResponse`.

### Endpoints downstream verificados (22 endpoints, NO se tocan)

`get_current_user` y `require_role` mantienen firma pública idéntica. Los 22 endpoints que dependen de ellos (categories: 3, products: 8, ingredients: 3, addresses: 5, users: 3) NO se modifican — sus tests deben pasar sin cambios (verificación de no-regresión).

### Tests

- **15 tests existentes** en `backend/tests/integration/test_auth.py` deben pasar sin modificaciones (contrato HTTP idéntico).
- **Tests downstream** que usan la fixture `auth_headers` (test_categories, test_ingredients, test_products, test_user_profile, test_delivery_addresses) deben pasar sin cambios.
- **No se agregan tests nuevos** — el refactor es comportamentalmente neutro al cliente HTTP. La atomicidad de `register` ya está cubierta implícitamente por `test_register_creates_user_and_token_pair` (cualquier fallo en el commit unificado se detectaría como ausencia del refresh token o del user_role).

### APIs externas

**Ninguna.** El contrato HTTP de cada endpoint (paths, request schemas, response schemas, status codes, error formats) queda **idéntico**. Frontend, integración n8n y cualquier consumidor externo no detectan el cambio.

### Estimación

**2.5–3.5 horas** (heredada del explore):
- 0.5 h: `AuthService` refactor (sync + with UoW + register atomic)
- 0.5 h: `dependencies.py` (`get_current_user` + `get_optional_user` con sesión directa)
- 0.5 h: `router.py` cleanup
- 0.5 h: `conftest.py` cleanup + verificar tests downstream
- 0.5 h: eliminar `get_db()` + docstrings obsoletos
- 0.5 h: buffer para corner cases (flush intermedios en `refresh`, atomicidad de `register`)

### Riesgos principales

- **R1 — Atomicidad de `register` post-refactor**: el bug latente (Usuario + UsuarioRol persistidos antes de que falle `_create_token_pair`) se cierra al envolver todo en un único `with UnitOfWork()`. Si el refactor se hace mal (ej. dejar `_create_token_pair` fuera del `with`), el bug se mantiene. Mitigación: tasks explícitos sobre el bloque único + scenarios de atomicidad en la spec.
- **R2 — Sesión directa en `get_current_user` vs UoW**: la sesión directa NO va al `__exit__` del UoW. Si alguien futuro intenta hacer una escritura accidental en `get_current_user`, no hay commit automático. Mitigación: documentar en el docstring que es read-only y agregar comentario que prohíbe escrituras.
- **R3 — Propagación a 22 endpoints downstream**: si la firma pública de `get_current_user` cambia accidentalmente (ej. cambia el tipo de retorno o pierde el chequeo de `is_active`), 22 endpoints se rompen. Mitigación: NO tocar firma pública; correr la suite completa después del refactor.
- **R4 — `conftest.py` después del cleanup**: si `override_get_db` se elimina antes de que `get_current_user` deje de usar `Depends(get_db)`, los tests fallan. Mitigación: orden explícito en tasks — primero refactorizar el código, después limpiar conftest.
- **R5 — Flush intermedios en `refresh`**: `refresh()` hace `flush()` después de `revoke_all_user_tokens` y `mark_token_as_revoked` para que los UPDATEs sean visibles antes del SELECT en `_create_token_pair`. Estos `flush()` son válidos dentro de un `with UnitOfWork()` — UoW solo hace commit en `__exit__`. Mitigación: tasks específicos sobre preservar los `flush()` intermedios.
