# Change: auth-backend

## ¿Qué?

Implementar el sistema completo de autenticación y autorización (RBAC) en el backend: registro de usuarios, login con JWT (access + refresh tokens), logout, renovación de tokens con rotación, protección de rutas por rol, y rate limiting en endpoints sensibles.

## ¿Por qué?

1. **Core del sistema**: Sin autenticación no hay control de acceso. Todo el resto del sistema (productos, pedidos, pagos) depende de saber QUIÉN es el usuario y QUÉ puede hacer.

2. **Historias críticas**: Este change cubre 7 historias de alta prioridad:
   - **US-001**: Registro de clientes
   - **US-002**: Login con JWT
   - **US-003**: Refresh token con rotación
   - **US-004**: Logout
   - **US-005**: Gestión de roles RBAC
   - **US-006**: Protección de rutas por rol
   - **US-073**: Rate limiting

3. **Seguridad**: Las reglas de negocio exigen:
   - RN-AU01: Contraseñas hasheadas con bcrypt
   - RN-AU02: Access token JWT (30 min) + Refresh token (7 días)
   - RN-AU04: Rotación de refresh tokens
   - RN-AU05: Detección de replay attacks
   - RN-AU06: Rate limiting en login
   - RN-AU08: Login no debe diferenciar "email no existe" de "contraseña incorrecta"

4. **Cuello de botella**: Cada módulo futuro (productos, pedidos, usuarios, direcciones) necesita:
   - Saber el `userId` del request (del JWT)
   - Validar permisos por rol (RBAC)
   - Sin esto, no se pueden implementar los endpoints protegidos.

## Historias cubiertas

| Historia | Descripción | Prioridad |
|----------|-------------|-----------|
| US-001 | Registro de nuevo cliente | Alta |
| US-002 | Login de usuario | Alta |
| US-003 | Refresh de token (rotación) | Alta |
| US-004 | Logout (invalidar refresh) | Media |
| US-005 | Gestión de roles (RBAC) | Alta |
| US-006 | Protección de rutas por rol | Alta |
| US-073 | Rate limiting en endpoints sensibles | Alta |

## Impacto

### Nuevos archivos

**Módulo auth** (`backend/app/modules/auth/`):
- `models.py` - Modelo RefreshToken
- `schemas.py` - DTOs: RegisterRequest, LoginRequest, TokenPairResponse
- `repository.py` - RefreshTokenRepository
- `service.py` - AuthService (login, register, refresh, logout)
- `router.py` - Endpoints: POST /auth/register, /auth/login, /auth/refresh, /auth/logout
- `dependencies.py` - get_current_user(), require_role()

**Shared**:
- `backend/shared/security.py` - JWT utils, password hashing
- `backend/shared/rate_limiter.py` - Rate limiting con slowapi

**Core**:
- `backend/core/config.py` - Añadir JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS

### Modificaciones

- `backend/main.py` - Registrar router auth + agregar rate limiting middleware
- `backend/app/modules/usuarios/models.py` - Revisar integración con auth

### Tests

- `backend/tests/modules/auth/` - Tests unitarios y de integración

## No incluye

- Frontend de login/registro (cambia US-007)
- Interceptor Axios (change US-008)
- Gestión de usuarios admin (change US-023)
- Perfil de usuario (change US-013)

## Dependencias

✅ **Cumplidas**:
- `database-schema-seed` - Tablas Usuario, Rol, UsuarioRol ya existen
- `backend-error-handling-validation` - RFC 7807 exceptions listas

## Criterios de aceptación del change

- [ ] Todos los endpoints responden con formato RFC 7807
- [ ] Rate limiting funciona en /auth/login y /auth/register
- [ ] JWT access token contiene: userId, email, roles[]
- [ ] Refresh tokens rotan correctamente (invalidan el anterior)
- [ ] Replay attack detectado → invalida todos los tokens del usuario
- [ ] Los tests pasan con coverage > 80%
