# Auth Endpoints

## Overview

Authentication system with JWT access tokens (30 min) and opaque refresh tokens (7 days).
Implements token rotation, replay attack detection, and rate limiting.

## Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/api/v1/auth/register` | Create new user account | 3/hour/IP |
| POST | `/api/v1/auth/login` | Authenticate and get tokens | 5/15min/IP |
| POST | `/api/v1/auth/refresh` | Exchange refresh token for new pair | 10/min/IP |
| POST | `/api/v1/auth/logout` | Revoke refresh token | N/A |
| GET | `/api/v1/auth/me` | Get current user info | N/A |

## Usage

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123",
    "nombre": "Juan",
    "apellido": "Perez"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123"
  }'
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Access Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## RBAC Dependencies

Protect routes by role:

```python
from fastapi import Depends
from backend.features.auth.dependencies import require_role

@router.get("/admin-only")
async def admin_endpoint(
    user=Depends(require_role("ADMIN")),
):
    return {"message": "Hello admin!"}
```

Available roles:
- `ADMIN` - Full system access
- `STOCK` - Product and inventory management
- `PEDIDOS` - Order management
- `CLIENT` - Customer (default on registration)

## Security Features

- **Password hashing**: bcrypt with cost factor 12
- **JWT access tokens**: 30 minute expiration, HS256 signed
- **Refresh tokens**: UUID v4, SHA-256 hashed in database
- **Token rotation**: Refresh tokens are single-use (revoked_at set on consumption)
- **Replay attack detection**: Reusing a revoked token triggers mass-revocation of all user tokens (RN-AU05)
- **Rate limiting**: Login (5/15min), Register (3/hour), Refresh (10/min)
- **Same error messages**: Invalid email and password return identical errors (RN-AU08)

## Error Responses

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Credenciales inválidas",
  "instance": "/api/v1/auth/login"
}
```
