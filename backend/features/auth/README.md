# Auth Endpoints

## Overview

Authentication uses JWT access tokens (30 min) and opaque refresh tokens (7 days), transported to browser clients as **HttpOnly cookies**. The backend still stores only refresh-token hashes and keeps token rotation, replay-attack detection, and rate limiting.

Development cookie defaults:

- `HttpOnly=true`
- `SameSite=Lax`
- `Secure=false`
- `access_token` path: `/api/v1`
- `refresh_token` path: `/api/v1/auth`

## Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/api/v1/auth/register` | Create account and set auth cookies | 3/hour/IP |
| POST | `/api/v1/auth/login` | Authenticate and set auth cookies | 5/15min/IP |
| POST | `/api/v1/auth/refresh` | Rotate refresh cookie and set a new pair | 10/min/IP |
| POST | `/api/v1/auth/logout` | Revoke refresh cookie and clear cookies | N/A |
| GET | `/api/v1/auth/me` | Get current user info from cookies | N/A |

## Usage

Use a cookie jar with curl:

```bash
# Login and save HttpOnly cookies
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password_123"}'

# Use saved cookies for authenticated requests
curl -b cookies.txt http://localhost:8000/api/v1/auth/me

# Refresh using refresh_token cookie and update the jar
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh

# Logout and clear cookies server-side
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

Login/register/refresh responses return session metadata, not raw tokens:

```json
{
  "user": {
    "id": 1,
    "nombre": "Juan",
    "apellido": "Perez",
    "email": "user@example.com",
    "roles": ["CLIENT"],
    "created_at": "2026-05-13T00:00:00Z"
  },
  "expires_in": 1800,
  "token_type": "cookie"
}
```

## RBAC Dependencies

Protect routes by role:

```python
from fastapi import Depends
from backend.features.auth.dependencies import require_role

@router.get("/admin-only")
async def admin_endpoint(user=Depends(require_role("ADMIN"))):
    return {"message": "Hello admin!"}
```

Available roles:
- `ADMIN` - Full system access
- `STOCK` - Product and inventory management
- `PEDIDOS` - Order management
- `CLIENT` - Customer (default on registration)

## Security Features

- **Password hashing**: bcrypt with cost factor 12
- **JWT access tokens**: 30 minute expiration, HS256 signed, stored in HttpOnly cookie
- **Refresh tokens**: UUID v4, SHA-256 hashed in database, stored in HttpOnly cookie
- **Token rotation**: Refresh tokens are single-use (`revoked_at` set on consumption)
- **Replay attack detection**: Reusing a revoked token mass-revokes active refresh tokens
- **Rate limiting**: Login (5/15min), Register (3/hour), Refresh (10/min)
- **Same error messages**: Invalid email and password return identical errors

## Error Responses

All errors follow RFC 7807 Problem Details format.
