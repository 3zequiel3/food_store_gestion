# users — módulo de perfil propio

Endpoints de auto-servicio de perfil para cualquier usuario autenticado (US-061, US-062, US-063).
Montado bajo `/api/v1/usuarios` (ver `backend/main.py`).

## Endpoints

| Método | Ruta            | Descripción                          | Auth |
|--------|-----------------|--------------------------------------|------|
| GET    | `/me`           | Ver perfil completo (con telefono)   | Cookie auth |
| PATCH  | `/me`           | Editar nombre / apellido / telefono  | Cookie auth |
| POST   | `/me/password`  | Cambiar contraseña (204 + revocar)   | Cookie auth |

## Ejemplos curl

```bash
# GET perfil propio
curl -b cookies.txt http://localhost:8000/api/v1/usuarios/me

# PATCH actualizar nombre
curl -X PATCH -b cookies.txt \
     -H "Content-Type: application/json" \
     -d '{"nombre": "Juan Carlos"}' \
     http://localhost:8000/api/v1/usuarios/me

# POST cambiar contraseña
curl -X POST -b cookies.txt \
     -H "Content-Type: application/json" \
     -d '{"password_actual": "old_pass", "password_nuevo": "new_pass_2024"}' \
     http://localhost:8000/api/v1/usuarios/me/password
```

## Comportamiento post-cambio de contraseña

Al recibir `204` de `POST /me/password`, el **frontend debe hacer logout local** (limpiar usuario en memoria/storage y redirigir a `/login`). Los refresh tokens son revocados inmediatamente; las cookies quedan inutilizables para refresh.
