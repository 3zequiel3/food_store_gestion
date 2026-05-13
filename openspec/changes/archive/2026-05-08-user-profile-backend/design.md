# Design: user-profile-backend

## 0. Contexto y alcance

Change #12 del roadmap (`docs/CHANGES.md:111-116`), primer change del Sprint 4 (Perfil y Direcciones — Backend). Incluye exactamente 3 endpoints REST (`GET /me`, `PATCH /me`, `POST /me/password`) bajo `/api/v1/users` y reutiliza al máximo la infraestructura ya consolidada en los changes de catálogo (`categories-backend`, `ingredients-backend`, `products-backend`).

**Reusos no negociables (NO redefinir):**
- Modelo: `Usuario` en `backend/features/users/models.py:44-96` (importar, no crear nuevo).
- Repos auxiliares: `RefreshTokenRepository` en `backend/features/auth/repository.py:18` (con `revoke_all_user_tokens` línea 39).
- Security utils: `hash_password` y `verify_password` en `backend/shared/security.py:19-26`.
- Auth dep: `get_current_user` en `backend/features/auth/dependencies.py:27`.
- Excepciones: `UnauthorizedError`, `NotFoundError`, `BusinessRuleError` en `backend/shared/exceptions.py` (handlers RFC 7807 ya registrados en `backend/main.py:108-119`).
- UoW: `UnitOfWork` y `Depends(get_uow)` desde `backend/dependencies.py:20`.

**Out of scope (registrado en proposal):**
- DELETE /users/me (borrar cuenta).
- Editar email (US-062 lo prohíbe textualmente; spec §3.1 lo trata como identificador UQ).
- Endpoints admin sobre otros usuarios (va en `admin-users-backend` #18).
- 2FA, OTP, recovery por email.

## 1. Estructura del módulo

El módulo `backend/features/users/` ya existe como stub:

```
backend/features/users/
├── __init__.py          (vacío)
├── models.py            (COMPLETO — Usuario, UsuarioRol — NO TOCAR)
├── repository.py        (vacío — completar con UserProfileRepository)
├── schemas.py           (vacío — completar con 3 schemas)
├── service.py           (vacío — completar con UserProfileService)
└── router.py            (3 endpoints stub `not_implemented` — REEMPLAZAR)
```

`backend/main.py:196` ya monta `users_router` en `/api/v1/users` con tag `users`. No hay que tocar `main.py`.

**Regla de oro de imports** (estricta — auditada en review):
```
router.py → service.py → unit_of_work.py → repository.py → models.py
                                              ↘ shared/security.py (sin layer arriba)
```
`repository.py` NO importa de `service.py` ni de `router.py`. `service.py` NO importa FastAPI ni Pydantic schemas como tipos de retorno (el router serializa con `model_validate`).

## 2. Schemas Pydantic v2 (`schemas.py`)

### `ProfileResponse`
Response de `GET /me` y `PATCH /me`. Diseño explícito sobre los campos para garantizar que **`password_hash` jamás se serialice** (no es opt-in, es blacklist por construcción — solo listamos los campos seguros).

```python
class ProfileResponse(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    apellido: str
    telefono: str | None
    roles: list[str]              # códigos: ["CLIENT"], ["CLIENT","ADMIN"], etc.
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}
```

Notas:
- `roles` se construye en el service haciendo `[r.codigo for r in user.roles]`. NO usar `from_attributes` para popularlo automáticamente — la M2M devuelve objetos `Rol`, no strings.
- `telefono` puede ser `null` (columna nullable).
- Se omite `is_active` y `eliminado_en` — no son del scope del cliente.

### `UpdateProfileRequest`
Body de `PATCH /me`. **Todos los campos opcionales** para soportar actualización parcial. El service usa `model_dump(exclude_unset=True)` para distinguir "no enviado" de "null explícito".

```python
class UpdateProfileRequest(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=80)
    apellido: str | None = Field(None, min_length=2, max_length=80)
    telefono: str | None = Field(
        None,
        pattern=r"^\+?[\d\s\-\(\)]{6,30}$",
        description="Formato libre internacional. Permite +, dígitos, espacios, guiones y paréntesis.",
    )

    model_config = {"extra": "forbid"}  # rechaza email/password/roles si los mandan
```

Notas:
- `min_length=2, max_length=80` igual que `RegisterRequest` (auth/schemas.py:28-39, "Per spec §6.1").
- `extra="forbid"` previene que un cliente intente smuggle `email` o `password` por este endpoint.
- Si `telefono` viene como string vacío `""`, no matchea el regex → 422 (deseado).

### `ChangePasswordRequest`
Body de `POST /me/password`.

```python
class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(..., min_length=1)
    password_nuevo: str = Field(..., min_length=8, max_length=128)

    model_config = {"extra": "forbid"}
```

Notas:
- `password_actual` con `min_length=1` (cualquier valor no-vacío); la verificación real es `verify_password` en el service.
- `password_nuevo` con `min_length=8` igual que `RegisterRequest` (RN-AU01 implica bcrypt — no hay regex de complejidad en la spec).
- `max_length=128` defensivo: bcrypt trunca a 72 bytes; valores absurdamente largos se rechazan en validación para evitar payload abuse.

## 3. Repository (`repository.py`)

```python
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.features.users.models import Usuario
from backend.shared.repository import BaseRepository


class UserProfileRepository(BaseRepository[Usuario]):
    """Repository for user profile operations (self-service only)."""

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def find_by_id_with_roles(self, user_id: int) -> Optional[Usuario]:
        """
        Read a Usuario eager-loading its roles[] relationship.

        Used by GET /me and PATCH /me to serialize ProfileResponse without
        triggering a lazy-load on `roles` after the session closes.
        Excludes soft-deleted users (eliminado_en IS NOT NULL).
        """
        query = (
            self._get_base_query()
            .where(Usuario.id == user_id)
            .options(selectinload(Usuario.roles))
        )
        return self.session.execute(query).scalar_one_or_none()
```

Decisiones del repo:
- Solo agregamos un método especializado (`find_by_id_with_roles`). El resto (read, update, delete) se hereda de `BaseRepository`.
- `selectinload(Usuario.roles)` → 2 queries deterministas: una a `users`, otra a `roles JOIN user_roles`. NO usamos `joinedload` (genera cartesianos cuando hay múltiples roles).
- `_get_base_query()` ya filtra `eliminado_en IS NULL` automáticamente (BaseRepository línea 49). Si `get_current_user` devolvió al user es porque está activo, pero el repo defensive-filter igual.
- Para `change_password` el service no necesita los roles → puede usar `read(user_id)` heredado (más barato).

## 4. Service (`service.py`)

```python
from backend.shared.unit_of_work import UnitOfWork
from backend.shared.security import hash_password, verify_password
from backend.shared.exceptions import (
    NotFoundError, UnauthorizedError, BusinessRuleError,
)
from backend.features.auth.repository import RefreshTokenRepository
from backend.features.users.repository import UserProfileRepository
from backend.features.users.schemas import (
    UpdateProfileRequest, ChangePasswordRequest,
)
from backend.features.users.models import Usuario


class UserProfileService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        uow.register_repository("usuarios", UserProfileRepository(uow.session))
        uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

    def get_profile(self, user_id: int) -> Usuario:
        user = self.uow.usuarios.find_by_id_with_roles(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        return user

    def update_profile(self, user_id: int, payload: UpdateProfileRequest) -> Usuario:
        user = self.uow.usuarios.find_by_id_with_roles(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return user  # no-op: PATCH sin campos válidos
        # Trim de strings (defensivo — Pydantic no trim por default)
        for key in ("nombre", "apellido"):
            if key in data and data[key] is not None:
                data[key] = data[key].strip()
                if not data[key]:
                    raise BusinessRuleError(f"El campo {key} no puede ser vacío")
        return self.uow.usuarios.update(user_id, **data)

    def change_password(self, user_id: int, payload: ChangePasswordRequest) -> None:
        user = self.uow.usuarios.read(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        # 1) Verificar password actual — siempre 401 genérico
        if not verify_password(payload.password_actual, user.password_hash):
            raise UnauthorizedError("Credenciales inválidas")
        # 2) Rechazar si el nuevo es igual al actual (evita revocar tokens en vano)
        if verify_password(payload.password_nuevo, user.password_hash):
            raise BusinessRuleError(
                "La nueva contraseña debe ser diferente de la actual"
            )
        # 3) Hashear y persistir
        user.password_hash = hash_password(payload.password_nuevo)
        self.uow.session.flush()
        # 4) Revocar TODOS los refresh tokens del usuario (RN-AU05)
        self.uow.refresh_tokens.revoke_all_user_tokens(user_id)
```

Decisiones del service:
- **Service NUNCA hace `uow.commit()`** — responsabilidad del router (deuda técnica D6, ver §7).
- `update_profile` valida trim (Pydantic no lo hace por default) y rechaza strings vacíos post-trim como `BusinessRuleError` 422.
- `change_password` chequea con `verify_password` — bcrypt comparison constant-time, sin leak de timing entre "user no existe" y "password incorrecta" (igual a RN-AU08).
- El error de password actual incorrecta es **401 con mensaje genérico** "Credenciales inválidas" (NO 422, NO "password incorrecto"). Razón: alinear con RN-AU08 (mismo mensaje para credenciales inválidas en login).
- La revocación de tokens corre DESPUÉS del flush del nuevo hash. Si la revocación falla, todo se rollbackea y la password no cambia (atomicidad UoW).
- `uow.session.flush()` explícito antes de revocar tokens — garantiza que el UPDATE de `password_hash` se ordena antes del UPDATE masivo de `refresh_tokens`. Sin flush, SQLAlchemy podría reordenar.

## 5. Router (`router.py`)

```python
from fastapi import APIRouter, Depends, Response, status

from backend.dependencies import get_uow
from backend.features.auth.dependencies import get_current_user
from backend.features.users.models import Usuario
from backend.features.users.schemas import (
    ChangePasswordRequest, ProfileResponse, UpdateProfileRequest,
)
from backend.features.users.service import UserProfileService
from backend.shared.unit_of_work import UnitOfWork

router = APIRouter()


def _to_profile_response(user: Usuario) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        telefono=user.telefono,
        roles=[r.codigo for r in user.roles],
        creado_en=user.creado_en,
        actualizado_en=user.actualizado_en,
    )


@router.get("/me", response_model=ProfileResponse, summary="Get own profile")
async def get_my_profile(
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    service = UserProfileService(uow)
    user = service.get_profile(current_user.id)
    return _to_profile_response(user)


@router.patch("/me", response_model=ProfileResponse, summary="Update own profile")
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    service = UserProfileService(uow)
    user = service.update_profile(current_user.id, payload)
    uow.commit()
    # Re-leer con roles para serializar response (el commit cierra la sesión transaccional)
    user = service.get_profile(current_user.id)
    return _to_profile_response(user)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    service = UserProfileService(uow)
    service.change_password(current_user.id, payload)
    uow.commit()
    return Response(status_code=204)
```

Decisiones del router:
- Cada endpoint usa `Depends(get_current_user)` — cualquier rol autenticado. NO se usa `require_role`.
- Las mutaciones (`PATCH`, `POST`) hacen `uow.commit()` después del service. El `GET` no hace commit (read-only).
- `get_my_profile` y `update_my_profile` usan `current_user.id` para el lookup — **NUNCA** aceptan un `user_id` vía path o body (RN-RB05: un cliente solo opera sobre sus propios datos).
- `update_my_profile` re-lee el perfil tras el commit para serializar `ProfileResponse` con `roles[]` correctamente populado.
- `change_my_password` retorna **204 No Content**. El frontend hará logout local al recibir el 204 (ver §7 risk #1).
- Ningún endpoint levanta `HTTPException` — los errores tipados del service llegan a los handlers RFC 7807 globales.

## 6. Manejo de errores (RFC 7807)

| Caso | Excepción | HTTP | Detail |
|------|-----------|------|--------|
| Sin token / token inválido | `UnauthorizedError` (lo levanta `get_current_user`) | 401 | "Token inválido o expirado" |
| Usuario no encontrado (defensive — get_current_user filtra activos) | `NotFoundError` | 404 | "Usuario no encontrado" |
| `password_actual` incorrecta | `UnauthorizedError` | **401** | "Credenciales inválidas" *(genérico, NO leak)* |
| `password_nuevo` igual a actual | `BusinessRuleError` | 422 | "La nueva contraseña debe ser diferente de la actual" |
| `nombre`/`apellido` vacío post-trim | `BusinessRuleError` | 422 | "El campo nombre no puede ser vacío" |
| `nombre`/`apellido` longitud inválida | Pydantic `RequestValidationError` | 422 | (auto, lista los fields) |
| `telefono` no matchea regex | Pydantic `RequestValidationError` | 422 | (auto) |
| `password_nuevo` < 8 chars | Pydantic `RequestValidationError` | 422 | (auto) |
| Body con campos extra (`email`, `password`) en PATCH | Pydantic `RequestValidationError` | 422 | (auto, `extra="forbid"`) |

Los handlers globales en `backend/main.py:108-119` ya producen RFC 7807 (`{type, title, status, detail, instance}`) — no se agregan handlers nuevos.

## 7. Riesgos de seguridad y decisiones explícitas

### Risk 1 — Access tokens JWT siguen activos 30 min post-cambio de password
**Comportamiento esperado, no bug.** Los access tokens son **stateless** (HS256, payload contiene `sub/email/roles/exp`) — no hay store que consultar para invalidarlos. Al cambiar password se revocan los **refresh tokens** (mediante `revoke_all_user_tokens`), pero el access token actual del cliente sigue válido hasta su expiración (30 min, RN-AU02).

**Implicación frontend:** al recibir 204 de `POST /me/password`, el cliente DEBE hacer logout local (borrar tokens de storage, redirigir a `/login`). Si no lo hace, el usuario sigue navegando con el access token viejo durante hasta 30 minutos pero **no podrá refrescarlo** — el primer 401 al expirar lo forzará a re-login.

**Mitigación adicional considerada y descartada:** mantener una blacklist de access tokens en Redis. Descartado para este change — agrega infra, no está en spec, y la ventana de 30 min es aceptable para una app de food delivery (no es un banco). Documentado para futuros changes si surge necesidad de "force logout immediate".

### Risk 2 — Mensaje de error en `password_actual` incorrecta debe ser genérico
**Decisión:** levantar `UnauthorizedError("Credenciales inválidas")` → **HTTP 401**, NO 422. Razón:

- 422 sugeriría "el formato del request es válido pero la regla de negocio falló" — leak semántico de "el password actual existe en el sistema pero no matchea".
- 401 alinea con el patrón de auth (RN-AU08): "no diferenciar email no existe vs password incorrecto". Mismo mensaje, mismo código, sin leak.
- El mensaje "Credenciales inválidas" no expone si el problema es `password_actual` o que el `user_id` del token no apunta a un usuario válido.

### Risk 3 — Validación de `telefono` con regex permisivo
**Decisión:** regex `^\+?[\d\s\-\(\)]{6,30}$`. Justificación:

- US-062 dice "Validación de formato de teléfono" pero no fija formato.
- Permite formatos internacionales típicos: `+54 11 1234-5678`, `(011) 1234-5678`, `+1-555-1234`, `5491112345678`.
- Min 6 chars (un teléfono local mínimo) y max 30 (acomoda extensiones largas con espacios).
- NO valida que el número exista o sea ruteable — eso es responsabilidad de un servicio externo (Twilio, etc.) fuera de scope.
- Falsos positivos posibles: `((((((`. Aceptable — el costo de un regex parser estricto (libphonenumber) no se justifica para un MVP de food store.

### Risk 4 — Race condition: dos cambios simultáneos de password
Escenario: el usuario abre dos pestañas y dispara `POST /me/password` desde ambas casi al mismo tiempo. La segunda llamada lee `password_hash` actualizado por la primera y `verify_password(payload.password_actual, ...)` falla → 401.

**Aceptado**: comportamiento correcto (la primera ya cambió la password). El usuario verá el error en la 2da pestaña.

### Risk 5 — Token introspection: `password_hash` JAMÁS en response
La columna `password_hash` está en el modelo `Usuario` y se carga en cada `find_by_id`. **`ProfileResponse` lo omite por construcción** (whitelist de campos, no blacklist). Verificación en review: `rg "password_hash" backend/features/users/router.py` → 0 matches; `rg "password_hash" backend/features/users/schemas.py` → 0 matches.

## 8. Decisión D6 — UoW: el service no hace commit

Idéntica deuda técnica reconocida en `categories-backend`, `ingredients-backend` y `products-backend`.

**Patrón actual:**
- Router obtiene `uow: UnitOfWork = Depends(get_uow)`.
- Service recibe el `uow` y lo usa SOLO para registrar repos y operar.
- **Service NUNCA llama `uow.commit()`**.
- Router llama `uow.commit()` después del service en mutaciones; en reads no commitea.

**Por qué se mantiene:**
- Consistencia con los 3 changes ya archivados.
- Cambiar el patrón ahora implicaría refactor masivo fuera del scope de este change chico.
- Documentado como deuda — se resolverá globalmente en un change futuro de tipo "uow-context-manager-refactor" (no priorizado en `docs/CHANGES.md`).

## 9. Tests sugeridos (`backend/tests/integration/test_user_profile.py`)

Patrón: clonar `test_categories.py` / `test_ingredients.py`. Reusar fixtures `client`, `sample_user`, `sample_roles`, `auth_headers` de `conftest.py`.

### Happy path
- `test_get_my_profile_returns_full_payload_with_telefono` — sembrar usuario con `telefono`, GET → 200 + body con todos los campos incluido `telefono`.
- `test_get_my_profile_includes_roles` — usuario con rol CLIENT → `roles: ["CLIENT"]` en response.
- `test_get_my_profile_omits_password_hash` — verificar que el JSON serializado NO contiene `"password_hash"`.
- `test_patch_nombre_only` — PATCH con solo `nombre` → 200, telefono y apellido sin cambios.
- `test_patch_all_fields_combined` — PATCH con nombre+apellido+telefono → 200.
- `test_patch_telefono_to_null` — PATCH con `telefono: null` → 200, columna queda `NULL`.
- `test_change_password_success` — POST con password_actual correcta + nueva válida → 204.

### Edge cases — validación
- `test_patch_nombre_empty_after_trim_returns_422` — PATCH con `"nombre": "   "` → 422 BusinessRuleError.
- `test_patch_nombre_too_short_returns_422` — `"nombre": "A"` → 422 (Pydantic min_length).
- `test_patch_nombre_too_long_returns_422` — 81 chars → 422.
- `test_patch_telefono_invalid_format_returns_422` — `"telefono": "abc"` → 422.
- `test_patch_telefono_empty_string_returns_422` — `"telefono": ""` no matchea regex → 422.
- `test_patch_with_extra_field_email_returns_422` — body con `"email": "..."` → 422 (`extra="forbid"`).
- `test_patch_with_extra_field_password_returns_422` — body con `"password": "..."` → 422.
- `test_change_password_too_short_returns_422` — `password_nuevo` 7 chars → 422.

### Edge cases — seguridad
- `test_change_password_with_wrong_actual_returns_401_generic` — POST con `password_actual` incorrecta → 401 + `detail: "Credenciales inválidas"` (NO "password incorrecto").
- `test_change_password_same_as_current_returns_422` — `password_nuevo == password_actual` → 422 BusinessRuleError.
- `test_endpoints_without_token_return_401` — GET/PATCH/POST sin Authorization header → 401.
- `test_endpoints_with_invalid_token_return_401` — `Bearer foo` → 401.

### Edge cases — invalidación de tokens (CRÍTICO)
- `test_change_password_revokes_all_refresh_tokens` — sembrar 2 refresh tokens activos, POST password → tras 204, lookup directo a la DB del test verifica que ambos tienen `revoked_at IS NOT NULL`.
- `test_refresh_after_password_change_returns_401` — login → recibir `refresh_token` → POST password → intentar `POST /api/v1/auth/refresh` con el viejo refresh_token → 401.
- `test_change_password_failed_does_not_revoke_tokens` — sembrar refresh tokens activos, intentar POST password con `password_actual` incorrecta → 401, los refresh tokens siguen `revoked_at IS NULL` (atomicidad: rollback).

### RBAC / cross-user isolation
- `test_user_can_only_see_own_profile` — usuario A se autentica, GET /me devuelve datos de A (no de B). Implícito en el diseño (no hay `user_id` en path), pero el test es defensive.
- `test_admin_user_can_use_endpoints_too` — usuario con rol ADMIN puede GET/PATCH/POST sus propios datos (cualquier rol autenticado).

## 10. Pre-flight check del propose

- ✅ Roadmap: `user-profile-backend` aparece en `docs/CHANGES.md:111` como change #12 del Sprint 4.
- ✅ Dependencias: `auth-backend` archivado en `openspec/changes/archive/2026-05-06-auth-backend/`. `auth-backend-stabilization` archivado en `openspec/changes/archive/2026-05-06-auth-backend-stabilization/`. `database-migrations` y `base-entities` archivados.
- ✅ Decisiones cerradas: D1-D5 explícitas en el prompt del usuario y registradas en proposal §"Decisiones cerradas". No surgieron assumptions nuevos sin cierre.
- ✅ Patrón a clonar: `categories-backend`, `ingredients-backend`, `products-backend` — los 3 archivados, todos con UoW + BaseRepository + service-no-commit.
