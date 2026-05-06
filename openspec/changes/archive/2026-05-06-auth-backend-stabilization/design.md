## Context

`auth-backend` se archivó el 2026-05-06 con sus 23 tareas tildadas, pero:

- La aplicación no arranca sin un parche defensivo (`backend/shared/database.py::get_db` faltaba). Ya aplicado en commit `6bd3592`.
- `pytest -q` desde `backend/` reporta **4 fallos + 18 OK + 22 errores**.
- Auditoría manual contra `docs/Integrador.txt` (ERD v5, sección 5.1) y `docs/Historias_de_usuario.txt` (RN-AU01..RN-AU10) reveló que el sub-agente que implementó el change inventó campos de modelo (`family_id`, `used`), desvió el prefijo de la API (`/api/auth/...` en vez de `/api/v1/auth/...`), no registró los exception handlers de RFC 7807 en `main.py`, y nunca corrió los tests al "completar" la TASK-20.

La regla canónica del proyecto (`CLAUDE.md`): *"Si una instrucción de los `.md` entra en conflicto con los `.txt`, gana la spec"*. El presente change estabiliza el módulo y lo realinea con la spec antes de que el roadmap apile más cambios encima (todo el Sprint 2 depende de auth funcional).

### Estado actual relevante

- `backend/features/auth/models.py::RefreshToken` declara `family_id: UUID` y `used: bool`. Ninguno está en el ERD ni en la migración inicial.
- `backend/alembic/versions/20260428_0001_8d61b8e48f6b_initial_schema.py` *ya* define `refresh_tokens` correcta: solo `id, user_id, token_hash, expires_at, revoked_at` + columnas de BaseModel. **El modelo Python derivó del schema ya migrado** — no hay que migrar nada nuevo.
- `backend/shared/error_handler.py` define todos los handlers RFC 7807, pero `backend/main.py` solo registra el de `RateLimitExceeded` y el genérico de `Exception` (que devuelve un cuerpo NO RFC 7807, conflictivo con `error-handling/spec.md`).
- `backend/dependencies.py` mantiene un engine + `SessionLocal` + `get_db_session` paralelos al `shared/database.py`. Verificación con `rg "get_db_session"` muestra **cero consumidores externos**.
- `backend/.env.example` está totalmente desync (lista `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `MP_*`, `CORS_ORIGINS`; el `Settings` actual lee `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `API_PORT`, `ENVIRONMENT`, `LOG_LEVEL`, `FRONTEND_URL`, `DATABASE_URL`).

## Goals / Non-Goals

**Goals**

1. `pytest -q` desde `backend/` retorna **0 failures + 0 errors**.
2. `uvicorn backend.main:app --reload` arranca sin excepciones de import o startup.
3. Los endpoints `/api/v1/auth/{register,login,refresh,logout,me}` cumplen contractualmente con RN-AU01..RN-AU10, US-001..US-006, US-073 y `docs/Integrador.txt` §3.1, §4, §5.1, §6.1.
4. Cualquier error producido por la app responde en formato RFC 7807 (`type, title, status, detail, instance`).
5. Spec auth (`openspec/specs/auth/spec.md` tras archive) queda como única fuente de verdad para futuros consumidores.

**Non-Goals**

- No implementar `auth-frontend-interceptor` (es el próximo change del roadmap).
- No tocar el flujo de `users-router`, `products-router`, `orders-router`, `payments-router` salvo el prefijo `/api/v1/` (que la spec exige y de paso evita 404 cuando aterricen los siguientes changes).
- No introducir migraciones Alembic nuevas — el schema en DB ya es el correcto.
- No agregar variables de entorno de MercadoPago (Sprint 7).

## Decisions

### D1 — Eliminar `RefreshToken.family_id`

**Decisión**: borrar `family_id` del modelo, repository, service, schemas y tests.

**Por qué**:
- ERD v5 (Integrador.txt §3.1) no contiene la columna.
- RN-AU05 dice textual: *"se revocan TODOS los tokens del usuario"*. No habla de "familia". `WHERE user_id = ?` cubre el contrato.
- La migración inicial no tiene la columna; solo el modelo Python la declaraba, lo que rompe SQLite (no soporta `UUID` PostgreSQL-specific).
- Mantenerlo es over-engineering puro: no hay caso de uso en US-001..US-006 que requiera familias separadas.

**Alternativas consideradas**:
- *Mantener `family_id` y agregar la columna a la migración*: rechazada — viola la spec ERD; agregar migración nueva sin justificación funcional.
- *Convertir `family_id` a `Integer` para SQLite*: rechazada — sigue sin estar en spec.

### D2 — Eliminar `RefreshToken.used` y modelar rotación con `revoked_at`

**Decisión**: borrar `used: bool`. La rotación setea `revoked_at` en el viejo. La detección de replay revisa `revoked_at IS NOT NULL`.

**Por qué**:
- ERD v5 lista solo `token_hash, expires_at, revoked_at` para RefreshToken (los campos ★ marcados como cambiados en v5; los standard de BaseModel se asumen).
- La migración inicial tampoco tiene `used`.
- Funcionalmente equivalente:
  - **Antes**: `used=True` después de rotar → si se reusa, replay attack.
  - **Después**: `revoked_at` set después de rotar → si se reusa, replay attack.
- Bonus: el logout también setea `revoked_at`, así que un replay después de logout también se detecta como compromiso (semántica más estricta que la versión con `used`, alineada con RN-AU05).

**Alternativas**:
- *Mantener `used` y agregar columna a la migración*: rechazada por las mismas razones que `family_id`.

### D3 — `token_hash` como `String(64)`

**Decisión**: declarar la columna como `String(64)` (no `String(255)`).

**Por qué**: SHA-256 hex es exactamente 64 caracteres; ERD lo dice CHAR(64). El modelo actual con `String(255)` desperdicia espacio y vulnera la restricción del schema. La migración inicial usa `String(length=255)` (mismo error). **Decisión adicional**: como cambiar de `String(255)` a `CHAR(64)` requiere una migración Alembic real (alter column), aceptamos el costo: generar `20260506_0002_align_refresh_tokens_with_erd.py` que solo hace `op.alter_column("refresh_tokens", "token_hash", type_=sa.String(length=64))`. No agregamos `family_id`/`used` (no existen ni en modelo nuevo ni en schema actual).

### D4 — Prefijo `/api/v1/`

**Decisión**: cambiar el prefijo de `auth_router` a `/api/v1/auth` en `main.py`. Por consistencia y para evitar drift futuro, también cambiar `users`, `products`, `orders`, `payments` (todos placeholders hoy). Actualizar `OAuth2PasswordBearer.tokenUrl` a `/api/v1/auth/login`. Actualizar `backend/features/auth/README.md` y todos los docstrings de los endpoints.

**Por qué**: `docs/Integrador.txt` §5 lo exige. Lo dejamos coherente ahora — corregirlo en otro change (cuando se implemente cada router real) duplica trabajo y rompe consumidores que ya empiecen a depender del path equivocado.

### D5 — Wiring de exception handlers en `main.py`

**Decisión**: registrar todos los handlers de `backend/shared/error_handler.py` en `main.py` durante el setup, en este orden:

```python
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from backend.shared.exceptions import (
    NotFoundError, ForbiddenError, UnauthorizedError,
    ConflictError, ValidationError, BusinessRuleError,
)
from backend.shared.error_handler import (
    not_found_handler, forbidden_handler, unauthorized_handler,
    conflict_handler, validation_error_handler, business_rule_handler,
    request_validation_handler, http_exception_handler, generic_exception_handler,
)

app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(ForbiddenError, forbidden_handler)
app.add_exception_handler(UnauthorizedError, unauthorized_handler)
app.add_exception_handler(ConflictError, conflict_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(BusinessRuleError, business_rule_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

**Por qué**: el spec `error-handling/spec.md` ya está vivo y dice "todas las respuestas usan RFC 7807", pero los handlers nunca se conectaron. Borramos también el `@app.exception_handler(Exception)` inline en `main.py` (devuelve un cuerpo no-RFC 7807 que rompe el contrato).

### D6 — Eliminar `backend/dependencies.py::engine/SessionLocal/get_db_session`

**Decisión**: borrar las definiciones duplicadas. Conservar solo `get_uow` y el placeholder `get_current_user` (que ya está marcado TODO).

**Verificación previa (mandatoria en apply, NO confiar en este design)**: `rg "get_db_session|from backend.dependencies" backend --type py` debe mostrar solo:
- el propio `dependencies.py`
- `backend/shared/database.py` (en un comment, no consume)
- imports de `get_uow` (siguen funcionando porque NO eliminamos `get_uow`)

Si aparece cualquier otro consumidor, **no eliminar**: en su lugar agregar al final de `dependencies.py`:

```python
# Backward-compat alias — prefer get_db from backend.shared.database for new code
from backend.shared.database import get_db as get_db_session  # noqa: F401
```

**Por qué**: dos engines paralelos contra la misma DB causan contención de pool y comportamientos sutilmente distintos en tests vs. producción. La versión "lazy" de `shared/database.py` es la canónica (la usa Alembic, el seed, los tests vía override y todos los routers).

### D7 — Tests: actualizar al formato RFC 7807 + python-jose API

**`test_register_duplicate_email`**:

```python
# Antes
assert data["code"] == "conflict"

# Después
assert data["status"] == 409
assert data["title"] == "Conflict"
```

**`test_create_access_token_contains_claims`**:

```python
# Antes (PyJWT API — no existe en jose)
payload = jwt.decode(token, options={"verify_signature": False})

# Después (jose API)
payload = jwt.get_unverified_claims(token)
```

**`test_decode_expired_token_returns_none`**:

```python
# Antes — jose tiene granularidad de segundos, seconds=0 es "ahora", no "expirado"
expires_delta=timedelta(seconds=0)

# Después
expires_delta=timedelta(seconds=-1)
```

**`test_refresh_expired_token`**: borrar la línea `family_id="12345678-..."` (el campo ya no existe en el modelo).

**Tests de URLs**: cambiar `/api/auth/...` → `/api/v1/auth/...` en todos los tests de integración.

### D8 — Schema `UserResponse`

**Decisión**: agregar `UserResponse` a `backend/features/auth/schemas.py`:

```python
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: EmailStr
    roles: list[str]
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2: enable from_orm
```

Usar como `response_model` en `GET /api/v1/auth/me` y devolver el usuario directamente (con `created_at` mapeado desde `BaseModel.creado_en`).

**Nota**: el campo en BaseModel se llama `creado_en` (español). Hay que mapearlo en el schema con un alias o construir el dict explícito en el handler. Decisión: construir el dict explícito en el handler (`{"id": user.id, ..., "created_at": user.creado_en}`) para no introducir alias y mantener el modelo limpio.

### D9 — `/register` mantiene `TokenPairResponse` (desviación spec aceptada)

**Decisión**: el endpoint `POST /api/v1/auth/register` retorna `201 TokenPairResponse`, no `UserResponse` como dice la spec §5.1.

**Por qué**:
- US-001 espera "registro deja al usuario logueado" (UX).
- El test `test_register_success` ya verifica el TokenPairResponse — fue escrito por el sub-agente original con la expectativa de US-001.
- El cambio a `UserResponse` rompe US-001 sin agregar valor.
- Lo documentamos como desviación intencional en la sección de "Spec note" del spec auth.

**Alternativa rechazada**: retornar `UserResponse` y hacer al frontend hacer un login adicional. Rechazada por friction de UX.

**Acción del usuario**: si quiere alinear estrictamente con la spec, abrir un follow-up change `auth-register-userresponse-alignment` que coordine frontend + backend juntos.

### D10 — `expires_in` derivado de settings

```python
# Antes
expires_in=30 * 60

# Después
from backend.config import settings
expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
```

Inmediato, low-risk, y evita que un cambio futuro de TTL en settings genere drift silencioso.

### D11 — `nombre`/`apellido` max 80

```python
# Antes
nombre: str = Field(..., min_length=2, max_length=100)
apellido: str = Field(..., min_length=2, max_length=100)

# Después (per spec §6.1)
nombre: str = Field(..., min_length=2, max_length=80)
apellido: str = Field(..., min_length=2, max_length=80)
```

El modelo Usuario en DB es `String(100)` — no rompe nada bajar la validación de Pydantic a 80.

### D12 — `.env.example` reescrito

```bash
# Database
DATABASE_URL=postgresql://food_user:food_password@localhost:5432/food_store

# JWT / Auth
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
API_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO

# CORS
FRONTEND_URL=http://localhost:5173
```

No incluye `MP_*` (vienen en Sprint 7) ni `CORS_ORIGINS` (no es campo de Settings, se calcula en property).

## Tabla de auditoría — drift detectado contra la spec

| Archivo | Estado actual | Spec dice | Acción |
|---|---|---|---|
| `auth/models.py::RefreshToken.family_id` | `Mapped[uuid.UUID]` declared | No existe en ERD §3.1 | **Eliminar** (D1) |
| `auth/models.py::RefreshToken.used` | `Mapped[bool] default False` | No existe en ERD §3.1 | **Eliminar** (D2) |
| `auth/models.py::RefreshToken.token_hash` | `String(255)` | `CHAR(64)` ERD §3.1 | Migración + `String(64)` (D3) |
| `auth/router.py` prefix | montado en `/api/auth/...` | `/api/v1/auth/...` §5.1 | Cambiar prefix en `main.py` (D4) |
| `auth/dependencies.py::oauth2_scheme.tokenUrl` | `/api/auth/login` | `/api/v1/auth/login` | Actualizar (D4) |
| `auth/router.py::oauth2_scheme.tokenUrl` | `/api/auth/login` | `/api/v1/auth/login` | Actualizar (D4) |
| `auth/service.py::_create_token_pair.expires_in` | hardcoded `30*60` | derivar de TTL configurable §6.1 | Settings-derived (D10) |
| `auth/schemas.py::RegisterRequest.nombre/apellido max` | `100` | `80` §6.1 | Bajar a 80 (D11) |
| `auth/schemas.py::UserResponse` | no existe | requerido por `/me` y opcionalmente `/register` §6.1 | Crear (D8) |
| `auth/router.py::/me` response | dict ad-hoc sin `created_at` | UserResponse incluye `created_at` §6.1 | Usar `UserResponse` (D8) |
| `main.py` exception handlers | solo `RateLimitExceeded` + genérico | RFC 7807 para todas | Registrar todos (D5) |
| `main.py::generic_exception_handler` (inline) | cuerpo `{detail, type}` no-RFC 7807 | RFC 7807 estricto | Borrar inline, usar el de `error_handler.py` (D5) |
| `dependencies.py::engine, SessionLocal, get_db_session` | duplicados de `shared/database.py` | sin redundancia | Borrar (D6) |
| `tests/integration/test_auth.py::test_register_duplicate_email` | assert `code == "conflict"` | RFC 7807 con `status, title` | Actualizar (D7) |
| `tests/integration/test_auth.py::test_refresh_expired_token` | usa `family_id=...` | sin `family_id` | Quitar línea (D7) |
| `tests/unit/test_security.py::test_create_access_token_contains_claims` | `jwt.decode(options=)` (PyJWT API) | jose API | `jwt.get_unverified_claims` (D7) |
| `tests/unit/test_security.py::test_decode_expired_token_returns_none` | `seconds=0` | `seconds=-1` (jose granularity) | Cambiar (D7) |
| `.env.example` | claves desync (`SECRET_KEY`, `MP_*`, `CORS_ORIGINS`) | `JWT_*`, `DATABASE_URL`, `API_PORT`, `ENVIRONMENT`, `LOG_LEVEL`, `FRONTEND_URL` | Reescribir (D12) |

## Risks / Trade-offs

[Riesgo] Cambiar el prefijo `/api/v1/` de routers placeholders (users, products, orders, payments) puede romper algún test indirecto.
→ Mitigación: `apply` ejecuta `pytest -q` después del cambio. Si rompe algo, se corrige inmediatamente.

[Riesgo] `D6` deletea `get_db_session` con `rg` como única evidencia. Si hay un import dinámico (raro pero posible), no aparecería.
→ Mitigación: la cláusula de fallback (alias) está documentada en D6. Apply la usa si el sub-agente encuentra un consumidor inesperado.

[Riesgo] `D9` deja la spec auth con una "Spec note" que explica una desviación contractual.
→ Mitigación: explícita y trazable. Si en el futuro el equipo decide alinear, abre un change dedicado.

[Riesgo] La migración nueva de `D3` (alter `token_hash` a `String(64)`) puede fallar si la DB de desarrollo tiene tokens existentes con longitud > 64.
→ Mitigación: tokens reales son SHA-256 (64 chars exactos) — no hay manera de que excedan el límite. Igualmente, antes del alter, el sub-agente puede ejecutar `SELECT MAX(LENGTH(token_hash)) FROM refresh_tokens` con `psql` MCP (read-only) si quiere paranoia extra. **No es bloqueante** — apply puede skipear esta sub-tarea si no hay consenso, dejando `String(255)` como deuda técnica menor.

[Trade-off] Eliminar `used` cambia la semántica del replay detection: ahora un token logged-out que se reusa también dispara la revocación masiva. La spec lo permite (RN-AU05 habla de "reuso de un refresh token ya utilizado" sin distinguir motivo).
→ Decisión: aceptado, es semántica más segura.

## Migration Plan

1. **Apply en orden estricto** (ver `tasks.md`).
2. **Tests primero**: ajustar `test_security.py` (D7 jose API) ANTES de tocar el modelo, para tener un baseline en verde de los unit tests.
3. **Modelo + service + repository + schemas** (D1, D2, D3, D8, D10, D11): los tests de integración fallan en compilación SQLite hasta que `family_id` y `used` desaparezcan; tras el cambio, esperamos los 22 errores se conviertan en pass o fail "real".
4. **Migración Alembic D3** (opcional según riesgo arriba): generar `align_refresh_tokens_with_erd.py`. Aplicar a la DB de desarrollo con `alembic upgrade head` antes de continuar.
5. **`main.py` exception handlers** (D5) + prefijo `/api/v1/` (D4).
6. **Tests integración**: actualizar URLs y formato RFC 7807 (D7).
7. **`dependencies.py` cleanup** (D6) con la verificación `rg` previa.
8. **`.env.example`** (D12).
9. **Verificación final**: `pytest -q` con 0F + 0E, `uvicorn` arranca, `curl /health`, `curl /nonexistent`, `curl /api/v1/auth/register`.

**Rollback**: cada commit es atómico por sub-tarea (D1, D2, ...). `git revert <sha>` de un commit aislado resuelve cualquier regresión sin tocar los demás. La migración Alembic D3 tiene downgrade auto-generable que vuelve `String(64)` a `String(255)`.

## Open Questions

1. **¿Aceptar D9?** Mantener `TokenPairResponse` en `/register` desvía de la spec §5.1. Default conservador del propose: aceptar la desviación, documentar como "Spec note" en el spec auth. Si el usuario prefiere alinear estricto, marcar como follow-up.
2. **¿Generar migración Alembic D3?** El alter `token_hash 255 → 64` es trivial, pero requiere crear un archivo nuevo y mover el head de Alembic. Alternativa: dejar `String(255)` como deuda menor y solo cambiar el modelo Python para que las nuevas escrituras respeten el límite (la columna sigue aceptando 255). Default del propose: **generar la migración** porque la deuda es 1 archivo y elimina drift de schema.
3. **`/api/v1/` para routers placeholder**: confirmar que cambiar prefix en routers vacíos no rompe nada que use `app.url_path_for(...)` u otro mecanismo no obvio. Default: hacerlo y dejar que `pytest` valide.
