# Tasks: auth-backend

## Configuración Base

- [x] **TASK-01**: Añadir variables JWT a `core/config.py`
  - `jwt_secret_key`, `jwt_algorithm`, `jwt_access_token_expire_minutes`, `jwt_refresh_token_expire_days`
  - Agregar a `.env.example` (sin valores reales)

- [x] **TASK-02**: Crear `shared/security.py` con utilidades de seguridad
  - `pwd_context` con bcrypt (cost factor 12)
  - `hash_password()`, `verify_password()`
  - `create_access_token()`, `decode_access_token()`
  - `create_refresh_token()` (UUID v4)

- [x] **TASK-03**: Crear `shared/rate_limiter.py` con slowapi
  - Configurar Limiter con get_remote_address
  - Exportar instance para usar en routers

## Modelo RefreshToken

- [x] **TASK-04**: Crear `app/modules/auth/models.py`
  - Modelo RefreshToken con campos: id, token_hash, user_id, family_id, used, revoked_at, expires_at, created_at
  - Índice único en token_hash
  - Relación con Usuario

## Schemas

- [x] **TASK-05**: Crear `app/modules/auth/schemas.py`
  - `RegisterRequest`: email, password (min 8), nombre
  - `LoginRequest`: email, password
  - `TokenPairResponse`: access_token, refresh_token, token_type, expires_in
  - `RefreshRequest`: refresh_token

- [x] **TASK-06**: Crear `app/modules/auth/repository.py`
  - `RefreshTokenRepository` heredando de `BaseRepository[RefreshToken]`
  - Método `get_by_token_hash(hash)`
  - Método `revoke_all_user_tokens(user_id)`
  - Método `revoke_family_tokens(family_id)`

## Service

- [x] **TASK-07**: Implementar `AuthService.register()`
- [x] **TASK-08**: Implementar `AuthService.login()`
- [x] **TASK-09**: Implementar `AuthService.refresh()`
- [x] **TASK-10**: Implementar `AuthService.logout()`
  - Buscar refresh token
  - Revocar (set revoked_at)

## Router

- [x] **TASK-11**: Crear `app/modules/auth/router.py`
  - `POST /api/v1/auth/register` con rate limit 3/hora
  - `POST /api/v1/auth/login` con rate limit 5/15min
  - `POST /api/v1/auth/refresh` con rate limit 10/min
  - `POST /api/v1/auth/logout` (protegido)
  - Todos los errores en formato RFC 7807

- [x] **TASK-12**: Crear `app/modules/auth/dependencies.py`
  - `get_current_user()` - extrae JWT del header, valida, retorna Usuario
  - `require_role(*roles)` - factory para validar roles
  - Manejar: token expirado, inválido, usuario no existe

## Integración

- [x] **TASK-13**: Registrar router en `main.py`
  - Incluir auth router con prefix `/api/v1`
  - Configurar rate limiting middleware global

## Tests

- [x] **TASK-14**: Tests unitarios de seguridad
  - `test_password_hashing()` - bcrypt funciona
  - `test_jwt_encode_decode()` - tokens válidos
  - `test_jwt_expiration()` - expira correctamente

- [x] **TASK-15**: Tests de integración - Registro
  - `test_register_success()` - crea usuario con rol CLIENT
  - `test_register_duplicate_email()` - retorna 409
  - `test_register_weak_password()` - retorna 422

- [x] **TASK-16**: Tests de integración - Login
  - `test_login_success()` - retorna tokens válidos
  - `test_login_invalid_email()` - 401, mismo mensaje
  - `test_login_invalid_password()` - 401, mismo mensaje
  - `test_login_rate_limit()` - 429 después de 5 intentos

- [x] **TASK-17**: Tests de integración - Refresh
  - `test_refresh_success()` - rota tokens
  - `test_refresh_expired()` - 401
  - `test_refresh_replay_attack()` - revoca todos, 401

- [x] **TASK-18**: Tests de integración - Logout
  - `test_logout_success()` - revoca token
  - `test_logout_unauthorized()` - 401 sin token

- [x] **TASK-19**: Tests de integración - RBAC
  - `test_protected_route_no_token()` - 401
  - `test_protected_route_wrong_role()` - 403
  - `test_protected_route_correct_role()` - 200

## Verificación Final

- [x] **TASK-20**: Ejecutar todos los tests
- [x] **TASK-21**: Verificar formato RFC 7807
- [x] **TASK-22**: Verificar rate limiting
- [x] **TASK-23**: Documentar en README
  - Endpoints disponibles
  - Cómo usar dependencias de auth
