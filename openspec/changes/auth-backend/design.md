# Design: auth-backend

## Arquitectura General

El módulo de autenticación sigue la arquitectura de capas del proyecto con la regla de oro de imports:

```
Router → Service → UoW → Repository → Model
```

## Modelo de Datos

### RefreshToken (nuevo)

```python
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"
    
    id: int = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)  # SHA-256 del token
    user_id: int = Field(foreign_key="usuario.id")
    family_id: uuid.UUID  # Para detectar replay attacks
    used: bool = False
    revoked_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Relaciones

```
Usuario 1:N RefreshToken
Usuario N:M Rol (vía UsuarioRol)
```

## Endpoints

| Método | Endpoint | Descripción | Público | Rate Limit |
|--------|----------|-------------|---------|------------|
| POST | `/api/v1/auth/register` | Crear cuenta cliente | ✅ | 3/hora/IP |
| POST | `/api/v1/auth/login` | Login | ✅ | 5/15min/IP |
| POST | `/api/v1/auth/refresh` | Renovar tokens | ✅ | 10/min/IP |
| POST | `/api/v1/auth/logout` | Cerrar sesión | ❌ | N/A |

## Schemas Pydantic

### RegisterRequest
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=2, max_length=100)
```

### LoginRequest
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

### TokenPairResponse
```python
class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
```

## Servicios

### AuthService

```python
class AuthService:
    async def register(self, data: RegisterRequest) -> Usuario:
        """Crea usuario con rol CLIENT automático."""
        
    async def login(self, data: LoginRequest, ip: str) -> TokenPairResponse:
        """Autentica usuario, aplica rate limiting, retorna tokens."""
        
    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        """Rota refresh token, detecta replay attacks."""
        
    async def logout(self, refresh_token: str) -> None:
        """Invalida refresh token (revoke)."""
```

## Seguridad

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# Hash: pwd_context.hash(password)
# Verify: pwd_context.verify(password, hash)
```

### JWT

```python
# Access Token (30 minutos)
payload = {
    "sub": str(user_id),
    "email": email,
    "roles": roles,
    "exp": now + 30 minutes
}

# Refresh Token (UUID v4 opaco)
refresh_token = uuid.uuid4()
# Almacenar SHA-256(refresh_token) en BD
```

### Rate Limiting (slowapi)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Login: 5 intentos por IP en 15 minutos
@router.post("/login")
@limiter.limit("5/15minute")
async def login(...)

# Registro: 3 intentos por IP en 1 hora
@router.post("/register")
@limiter.limit("3/hour")
async def register(...)
```

## Dependencias de FastAPI

### get_current_user

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Usuario:
    """Extrae y valida JWT, retorna usuario."""
    
async def require_role(*roles: str):
    """Factory de dependencias para validar roles."""
    async def check_role(user: Usuario = Depends(get_current_user)):
        if not any(r.codigo in roles for r in user.roles):
            raise ForbiddenError("Insufficient permissions")
        return user
    return check_role
```

## Flujos

### Registro (US-001)

```
POST /auth/register
├── Validar email único
├── Hash password (bcrypt)
├── Crear Usuario
├── Asignar rol CLIENT (automático)
├── Crear tokens (access + refresh)
└── Retornar TokenPairResponse
```

### Login (US-002)

```
POST /auth/login
├── Rate limit check
├── Buscar usuario por email
├── Verificar password (bcrypt)
├── Si falla: mismo mensaje (RN-AU08)
├── Si OK: crear tokens
└── Retornar TokenPairResponse
```

### Refresh (US-003)

```
POST /auth/refresh
├── Buscar refresh token por hash
├── Validar no expirado, no usado, no revocado
├── Si usado: REVOCAR TODOS los tokens del usuario (RN-AU05)
├── Marcar como usado
├── Crear NUEVO par de tokens (rotación)
└── Retornar TokenPairResponse
```

### Logout (US-004)

```
POST /auth/logout
├── Requiere autenticación
├── Revocar refresh token (soft delete)
└── 204 No Content
```

## Manejo de Errores

| Escenario | Excepción | HTTP | RFC 7807 |
|-----------|-----------|------|----------|
| Email duplicado | ConflictError | 409 | title: "User already exists" |
| Credenciales inválidas | UnauthorizedError | 401 | title: "Invalid credentials" (mismo mensaje) |
| Rate limit excedido | HTTPException | 429 | slowapi maneja headers |
| Token expirado | UnauthorizedError | 401 | title: "Token expired" |
| Token inválido | UnauthorizedError | 401 | title: "Invalid token" |
| Replay attack detectado | UnauthorizedError | 401 | title: "Token reuse detected" |

## Tests

### Unitarios

- `test_password_hashing()` - bcrypt funciona correctamente
- `test_jwt_encode_decode()` - tokens se crean y validan
- `test_token_expiration()` - expiración funciona

### Integración

- `test_register_success()` - flujo completo de registro
- `test_login_success()` - login retorna tokens válidos
- `test_login_invalid_credentials()` - mismo mensaje de error
- `test_refresh_rotation()` - rotación funciona
- `test_replay_attack()` - detecta y revoca todos los tokens
- `test_rate_limit_login()` - bloquea después de 5 intentos

## Estructura de Archivos

```
backend/
├── app/
│   └── modules/
│       └── auth/
│           ├── __init__.py
│           ├── models.py          # RefreshToken
│           ├── schemas.py         # Request/Response DTOs
│           ├── repository.py      # RefreshTokenRepository
│           ├── service.py         # AuthService
│           ├── router.py          # FastAPI routes
│           └── dependencies.py    # get_current_user, require_role
├── shared/
│   ├── security.py                # JWT utils, password hashing
│   └── rate_limiter.py            # Config slowapi
├── core/
│   └── config.py                  # JWT settings
└── tests/
    └── modules/
        └── auth/
            ├── test_service.py
            ├── test_router.py
            └── conftest.py
```

## Configuración

### .env

```bash
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### core/config.py

```python
class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
```
