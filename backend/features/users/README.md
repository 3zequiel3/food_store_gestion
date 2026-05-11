# users — módulo de perfil propio

Endpoints de auto-servicio de perfil para cualquier usuario autenticado (US-061, US-062, US-063).
Montado bajo `/api/v1/usuarios` (ver `backend/main.py`).

## Endpoints

| Método | Ruta            | Descripción                          | Auth |
|--------|-----------------|--------------------------------------|------|
| GET    | `/me`           | Ver perfil completo (con telefono)   | JWT  |
| PATCH  | `/me`           | Editar nombre / apellido / telefono  | JWT  |
| POST   | `/me/password`  | Cambiar contraseña (204 + revocar)   | JWT  |

## Ejemplos curl

```bash
# GET perfil propio
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/usuarios/me

# PATCH actualizar nombre
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"nombre": "Juan Carlos"}' \
     http://localhost:8000/api/v1/usuarios/me

# POST cambiar contraseña
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"password_actual": "old_pass", "password_nuevo": "new_pass_2024"}' \
     http://localhost:8000/api/v1/usuarios/me/password
```

## Comportamiento post-cambio de contraseña

Al recibir `204` de `POST /me/password`, el **frontend debe hacer logout local** (borrar tokens del
storage y redirigir a `/login`). Los refresh tokens son revocados inmediatamente; el access token
sigue válido hasta su expiración natural (~30 min) pero no puede ser refrescado.
