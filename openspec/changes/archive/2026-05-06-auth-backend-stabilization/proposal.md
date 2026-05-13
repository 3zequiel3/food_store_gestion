## Why

El change `auth-backend` se archivó el 2026-05-06 con sus 23 tareas tildadas, pero la implementación no es funcional ni está alineada con la spec canónica:

1. **La aplicación no arranca** sin un fix defensivo (`get_db` no estaba en `shared/database.py`). El parche ya se aplicó (commit `6bd3592`), pero hay otros problemas debajo.
2. **`pytest -q` reporta 4 fallos + 18 OK + 22 errores** porque el sub-agente que implementó `auth-backend` nunca corrió los tests al cerrar la TASK-20.
3. **Spec drift profundo**: una auditoría forense contra `docs/Integrador.txt` y `docs/Historias_de_usuario.txt` reveló que el sub-agente inventó campos y desvió la API en varios puntos, violando la regla canónica del proyecto: *"Si una instrucción de los `.md` entra en conflicto con los `.txt`, gana la spec."*

Este change estabiliza la implementación y la realinea con la spec antes de seguir construyendo encima (todo el roadmap a partir del Sprint 2 depende de auth).

## What Changes

### Drift de modelo y datos

- **BREAKING — `RefreshToken.family_id`**: Eliminar el campo (UUID) — no figura en el ERD del Integrador.txt sección 3.1 y no es necesario para RN-AU05. La revocación por replay attack opera por `user_id` directamente.
- **BREAKING — `RefreshToken.used`**: Eliminar el flag — tampoco figura en el ERD ni en la migración inicial. La rotación se modela con `revoked_at`: refrescar marca el token viejo como revocado, lo que cubre rotación + replay detection con un solo campo.
- **`RefreshToken.token_hash`**: Cambiar `String(255)` a `CHAR(64)` (SHA-256 hex tiene exactamente 64 chars, ERD lo exige).
- **Migración Alembic**: la migración inicial `20260428_0001` *ya* tiene la tabla `refresh_tokens` correctamente alineada con la spec (sin `family_id`, sin `used`). El modelo Python es lo que está mal. **No hace falta una migración nueva**: ajustamos el modelo para que coincida con el schema ya migrado.

### Drift de API

- **BREAKING — Prefijo `/api/v1/`**: La spec (sección 5) define `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`. El código usa `/api/auth/...`. Corregir en `main.py`, `oauth2_scheme.tokenUrl`, README y docstrings del módulo auth.
- **`expires_in` hardcoded**: En `service._create_token_pair` está clavado en `30 * 60` segundos. Derivar de `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60` para que un cambio de config no genere drift.
- **Schemas — límites de longitud**: `RegisterRequest.nombre` y `apellido` están en `min=2, max=100`. La spec sección 6.1 dice `min 2 max 80`. Ajustar.
- **Endpoint `/me` response**: la spec define `UserResponse` con `id, nombre, apellido, email, roles[], created_at`. El handler actual omite `created_at`. Agregarlo y crear el schema `UserResponse` (que faltaba).
- **Endpoint `/register` response**: la spec dice `201 UserResponse`, pero el código retorna `TokenPairResponse`. **Decisión**: mantener `TokenPairResponse` porque US-001 espera "registro deja al usuario logueado", y el test de integración lo verifica. Documentar como desviación intencional con justificación de UX, NO archivar como compatible con la spec hasta que el usuario apruebe.

### Bugs de tests (RN del proyecto: tests deben pasar antes de cerrar)

- **22 errores de compilación SQLite**: causados por `family_id UUID` (PostgreSQL-specific) contra el SQLite in-memory de los tests. Se eliminan al borrar el campo.
- **`test_create_access_token_contains_claims`**: usa `jwt.decode(token, options={"verify_signature": False})`, API de PyJWT. python-jose no acepta esa firma — cambiar a `jwt.get_unverified_claims(token)`.
- **`test_decode_expired_token_returns_none`**: `timedelta(seconds=0)` no produce un token expirado en jose (granularidad de segundos). Cambiar a `timedelta(seconds=-1)`.
- **`test_register_duplicate_email`**: assertea `data["code"] == "conflict"`, formato legacy del backend. La spec de error-handling (vigente en `openspec/specs/error-handling/spec.md`) define RFC 7807: `{type, title, status, detail, instance}`. Actualizar el test para assertar `data["status"] == 409` y `data["title"] == "Conflict"`.
- **`test_login_*_message`**: dependen de `data["detail"]`. RFC 7807 expone `detail` igual, así que estos tests están OK — solo verificar que pasen una vez los handlers se registren.

### Wiring de exception handlers

- `main.py` nunca registra los handlers de `shared/error_handler.py`. Cualquier `UnauthorizedError`, `ConflictError`, `NotFoundError`, etc., termina cayendo al genérico 500. Registrar todos los handlers (`unauthorized_handler`, `forbidden_handler`, `not_found_handler`, `conflict_handler`, `validation_error_handler`, `business_rule_handler`, `request_validation_handler`, `http_exception_handler`, `generic_exception_handler`) durante el startup.

### Limpieza de código

- **`backend/dependencies.py` deprecation**: tiene un `engine`/`SessionLocal`/`get_db_session` paralelos a `shared/database.py`. Verificación con `rg "get_db_session"` confirma **cero consumidores externos**. Eliminar las definiciones duplicadas; mantener solo `get_uow` y `get_current_user` (placeholder). El módulo auth ya importa `get_db` desde `shared/database.py` correctamente.
- **`.env.example` desync**: lista `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `MP_*`, `CORS_ORIGINS`. El `Settings` actual usa `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `API_PORT`, `ENVIRONMENT`, `LOG_LEVEL`, `FRONTEND_URL`, `DATABASE_URL`. Sincronizar el archivo (sin preempar variables MP que llegan en Sprint 7).

### Verificaciones obligatorias (apply debe ejecutarlas y pegar output real)

- `pytest -q` desde `backend/` retorna **0 failures + 0 errors**.
- `uvicorn backend.main:app --reload` arranca sin `ImportError` ni excepciones de startup.
- `curl http://localhost:8000/health` retorna `{"status": "ok", ...}` 200.
- `curl http://localhost:8000/nonexistent` retorna 404 con cuerpo RFC 7807 (`type/title/status/detail/instance`).
- `curl -X POST http://localhost:8000/api/v1/auth/register -d '...'` retorna 201 con TokenPairResponse.

## Capabilities

### New Capabilities

- `auth`: Capacidad de autenticación y autorización (registro, login, refresh con rotación, logout, RBAC, rate limiting). El change `auth-backend` archivado nunca creó este spec — lo creamos ahora con los requisitos correctos derivados de RN-AU01..RN-AU10 y US-001..US-006, US-073.

### Modified Capabilities

- *Ninguna*. La capacidad `error-handling` no cambia sus requisitos: solo se la conecta correctamente al `main.py` (que es implementación, no contrato).

## Impact

### Código modificado

- `backend/features/auth/models.py` — drop `family_id`, drop `used`, ajustar `token_hash` a `String(64)`.
- `backend/features/auth/repository.py` — drop `revoke_family_tokens`, drop `mark_token_as_used`. Conservar y ajustar `revoke_all_user_tokens` (ya OK), agregar `mark_token_as_revoked(token_id)` que setea `revoked_at`.
- `backend/features/auth/service.py` — remover toda referencia a `family_id` y `used`. La rotación setea `revoked_at` en el viejo, crea uno nuevo. La detección de replay chequea `revoked_at IS NOT NULL` y revoca todos los tokens del usuario. Derivar `expires_in` de settings.
- `backend/features/auth/schemas.py` — ajustar `nombre`/`apellido` max a 80, agregar `UserResponse`.
- `backend/features/auth/router.py` — agregar `UserResponse` como response_model de `/register` (si decisión es UserResponse) o documentar la desviación. Ajustar `oauth2_scheme.tokenUrl` a `/api/v1/auth/login`.
- `backend/features/auth/dependencies.py` — ajustar `oauth2_scheme.tokenUrl`. Sin más cambios.
- `backend/features/auth/README.md` — actualizar URLs a `/api/v1/...`.
- `backend/main.py` — registrar TODOS los exception handlers desde `shared/error_handler.py`. Cambiar prefijo de routers a `/api/v1/...` (auth, users, products, orders, payments). Agregar 404 catch-all para que `Starlette HTTPException` también pase por RFC 7807.
- `backend/dependencies.py` — borrar `engine`, `SessionLocal`, `get_db_session`. Conservar `get_uow` y placeholder `get_current_user`.
- `backend/.env.example` — reescribir con las claves que `Settings` realmente lee.
- `backend/tests/conftest.py` — los fixtures funcionan; verificar que el `client` use `get_db` (ya OK).
- `backend/tests/integration/test_auth.py` — actualizar `test_register_duplicate_email` al formato RFC 7807, eliminar referencias a `family_id` en `test_refresh_expired_token`. Actualizar URLs a `/api/v1/auth/...`.
- `backend/tests/unit/test_security.py` — fix `jwt.decode(options=)` → `jwt.get_unverified_claims`. Fix expiración con `timedelta(seconds=-1)`.

### Sin migración Alembic nueva

La migración inicial `20260428_0001_8d61b8e48f6b_initial_schema.py` ya define `refresh_tokens` con las columnas correctas según ERD (sin `family_id`, sin `used`). El drift fue solo del modelo Python — no hay schema en DB que cambiar. No agregamos un downgrade que dropee columnas inexistentes.

### Spec auth nueva

Crear `openspec/specs/auth/spec.md` con los requisitos derivados de:
- RN-AU01..RN-AU10 (`docs/Historias_de_usuario.txt`)
- US-001..US-006, US-073
- ERD sección 3.1 + endpoints sección 5.1 (`docs/Integrador.txt`)

Incluir explícitamente:
- Estructura de `RefreshToken` (sin `family_id`, sin `used`).
- Rate limits: `5/15min` login, `3/hour` register, `10/min` refresh.
- Algoritmo de rotación basado en `revoked_at`.
- Detección de replay attack y su consecuencia (revocación de todos los tokens del usuario).
- Endpoints exactos con sus prefijos `/api/v1/`.
- Roles fijos: ADMIN(1), STOCK(2), PEDIDOS(3), CLIENT(4).

### Riesgos

1. **Decisión de `/register` response**: mantener `TokenPairResponse` (UX) vs. mover a `UserResponse` (spec). El usuario debería confirmar; default conservador es mantener tokens y documentar como desviación aceptada.
2. **Prefijo `/api/v1/`**: cambiar el prefix afecta routers de users/products/orders/payments — todos están vacíos hoy (placeholder), pero si alguno tiene tests aguas arriba, hay que verificarlos.
3. **Eliminación de `used`**: cambia la semántica del replay detection (de "ya consumido" a "ya revocado"). Es funcionalmente equivalente y se ajusta al ERD, pero hay que dejarlo bien explicado en el design para que apply no se confunda.

### Quien se ve afectado

- Cualquier consumidor futuro de `/api/v1/auth/...` (todos los frontends, mobile si lo hubiera).
- El próximo change del roadmap: `auth-frontend-interceptor` — debe consumir las URLs corregidas.
- Cualquier change que dependa de `auth-backend` (toda la cadena del Sprint 2 en adelante: categories-backend, ingredients-backend, products-backend, orders, payments, etc.).
