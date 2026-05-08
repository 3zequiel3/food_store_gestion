## 1. Schemas Pydantic v2

- [x] 1.1 En `backend/features/users/schemas.py`: importar `BaseModel`, `Field`, `EmailStr` de `pydantic` y `datetime` de `datetime`.
- [x] 1.2 Definir `ProfileResponse(BaseModel)` con: `id: int`, `email: EmailStr`, `nombre: str`, `apellido: str`, `telefono: str | None`, `roles: list[str]`, `creado_en: datetime`, `actualizado_en: datetime`. Agregar `model_config = {"from_attributes": True}`. **NO incluir `password_hash` ni `is_active` ni `eliminado_en`.**
- [x] 1.3 Definir `UpdateProfileRequest(BaseModel)`:
  - `nombre: str | None = Field(None, min_length=2, max_length=80)`
  - `apellido: str | None = Field(None, min_length=2, max_length=80)`
  - `telefono: str | None = Field(None, pattern=r"^\+?[\d\s\-\(\)]{6,30}$")`
  - `model_config = {"extra": "forbid"}` para rechazar `email`/`password`/etc.
  - Docstring: "El service usa `model_dump(exclude_unset=True)` para distinguir 'no enviado' de 'null explícito'."
- [x] 1.4 Definir `ChangePasswordRequest(BaseModel)`:
  - `password_actual: str = Field(..., min_length=1)`
  - `password_nuevo: str = Field(..., min_length=8, max_length=128)`
  - `model_config = {"extra": "forbid"}`.
- [x] 1.5 Verificar con `rg "password_hash" backend/features/users/schemas.py` → 0 matches en campos declarados (solo en comentarios/docstrings).

## 2. Repository

- [x] 2.1 En `backend/features/users/repository.py`: importar `Optional` de `typing`, `select` de `sqlalchemy`, `Session` y `selectinload` de `sqlalchemy.orm`, `Usuario` de `backend.features.users.models`, `BaseRepository` de `backend.shared.repository`.
- [x] 2.2 Crear `class UserProfileRepository(BaseRepository[Usuario])` con `__init__(self, session: Session)` que llame `super().__init__(session, Usuario)`.
- [x] 2.3 Implementar `find_by_id_with_roles(self, user_id: int) -> Optional[Usuario]`:
  - Construir query con `self._get_base_query().where(Usuario.id == user_id).options(selectinload(Usuario.roles))`.
  - Devolver `self.session.execute(query).scalar_one_or_none()`.
  - Docstring: "Excluye soft-deleted (heredado de `_get_base_query`). Eager-load de roles para serializar `ProfileResponse` post-commit."
- [x] 2.4 Verificar que NO se agregaron métodos extras (no `find_by_email`, no `list_users`, etc. — fuera de scope).

## 3. Service

- [x] 3.1 En `backend/features/users/service.py`: importar `UnitOfWork`, `hash_password`, `verify_password`, las excepciones (`NotFoundError`, `UnauthorizedError`, `BusinessRuleError`), `RefreshTokenRepository`, `UserProfileRepository`, los schemas (`UpdateProfileRequest`, `ChangePasswordRequest`) y el modelo `Usuario`.
- [x] 3.2 Crear `class UserProfileService` con `__init__(self, uow: UnitOfWork)` que:
  - Guarde `self.uow = uow`.
  - Registre `uow.register_repository("usuarios", UserProfileRepository(uow.session))`.
  - Registre `uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))`.
- [x] 3.3 Implementar `get_profile(self, user_id: int) -> Usuario`:
  - `user = self.uow.usuarios.find_by_id_with_roles(user_id)`.
  - Si `user is None` → `raise NotFoundError("Usuario no encontrado")`.
  - Devolver `user`.
- [x] 3.4 Implementar `update_profile(self, user_id: int, payload: UpdateProfileRequest) -> Usuario`:
  - Leer con `find_by_id_with_roles` (no `read` heredado — necesitamos roles para serializar).
  - Si no existe → `NotFoundError`.
  - `data = payload.model_dump(exclude_unset=True)`.
  - Si `data` está vacío → devolver el `user` directamente (PATCH sin cambios = no-op).
  - Para cada `key in ("nombre", "apellido")` que esté en `data` y no sea `None`: aplicar `.strip()`. Si queda vacío → `BusinessRuleError(f"El campo {key} no puede ser vacío")`.
  - `return self.uow.usuarios.update(user_id, **data)` (heredado de `BaseRepository`).
- [x] 3.5 Implementar `change_password(self, user_id: int, payload: ChangePasswordRequest) -> None`:
  - `user = self.uow.usuarios.read(user_id)` (sin roles — no los necesita).
  - Si no existe → `NotFoundError("Usuario no encontrado")`.
  - Si `not verify_password(payload.password_actual, user.password_hash)` → `raise UnauthorizedError("Credenciales inválidas")`. **Mensaje genérico, NO "password incorrecto".**
  - Si `verify_password(payload.password_nuevo, user.password_hash)` (la nueva es igual a la actual) → `raise BusinessRuleError("La nueva contraseña debe ser diferente de la actual")`.
  - `user.password_hash = hash_password(payload.password_nuevo)`.
  - `self.uow.session.flush()` — garantiza orden de persistencia antes del UPDATE masivo.
  - `self.uow.refresh_tokens.revoke_all_user_tokens(user_id)`.
  - **NO retornar nada** (None).
- [x] 3.6 Verificar que NINGÚN método del service llama `uow.commit()` ni `session.commit()` (D6 — el commit es del router).
- [x] 3.7 Verificar con `rg "uow.commit\(\)|session.commit\(\)" backend/features/users/service.py` → 0 matches.

## 4. Router (reemplazar stubs)

- [x] 4.1 En `backend/features/users/router.py`: BORRAR los 3 endpoints stub (`list_users`, `get_user`, `create_user`).
- [x] 4.2 Imports: `APIRouter`, `Depends`, `Response`, `status` de `fastapi`; `get_uow` de `backend.dependencies`; `get_current_user` de `backend.features.auth.dependencies`; `Usuario` de `backend.features.users.models`; los 3 schemas de `backend.features.users.schemas`; `UserProfileService` de `backend.features.users.service`; `UnitOfWork` de `backend.shared.unit_of_work`.
- [x] 4.3 Crear `router = APIRouter()` (sin prefix — se aplica en `main.py`).
- [x] 4.4 Helper privado `_to_profile_response(user: Usuario) -> ProfileResponse`:
  - Construir explícitamente con todos los campos (id, email, nombre, apellido, telefono, roles=[r.codigo for r in user.roles], creado_en, actualizado_en).
  - Razón: M2M `roles` devuelve objetos `Rol`, no strings — Pydantic `from_attributes` no los serializa correctamente.
- [x] 4.5 Implementar `GET /me` con `response_model=ProfileResponse`:
  - Dependencias: `current_user: Usuario = Depends(get_current_user)`, `uow: UnitOfWork = Depends(get_uow)`.
  - `service = UserProfileService(uow)`.
  - `user = service.get_profile(current_user.id)`.
  - Devolver `_to_profile_response(user)`. **NO commit** (read-only).
- [x] 4.6 Implementar `PATCH /me` con `response_model=ProfileResponse`:
  - Dependencias: `payload: UpdateProfileRequest`, `current_user: Usuario = Depends(get_current_user)`, `uow: UnitOfWork = Depends(get_uow)`.
  - `service = UserProfileService(uow)`.
  - `service.update_profile(current_user.id, payload)`.
  - `uow.commit()`.
  - `user = service.get_profile(current_user.id)` — re-lee con roles eager-loaded después del commit.
  - Devolver `_to_profile_response(user)`.
- [x] 4.7 Implementar `POST /me/password` con `status_code=status.HTTP_204_NO_CONTENT`:
  - Dependencias: `payload: ChangePasswordRequest`, `current_user: Usuario = Depends(get_current_user)`, `uow: UnitOfWork = Depends(get_uow)`.
  - `service = UserProfileService(uow)`.
  - `service.change_password(current_user.id, payload)`.
  - `uow.commit()`.
  - `return Response(status_code=204)`.
- [x] 4.8 Verificar que NINGÚN endpoint:
  - Acepta `user_id` en path o body (RN-RB05 — solo opera sobre el propio perfil).
  - Levanta `HTTPException` directamente.
  - Hace `uow.rollback()` manual (lo maneja el dependency wrapper de `get_uow`).
- [x] 4.9 Verificar con `rg "user_id" backend/features/users/router.py` → solo aparece en el helper interno y como `current_user.id`, NO en path params.

## 5. Wiring en main.py

- [x] 5.1 Verificar que `backend/main.py:67` ya tiene `from backend.features.users.router import router as users_router`. **NO agregar nada — ya está.**
- [x] 5.2 Verificar que `backend/main.py:196` ya tiene `app.include_router(users_router, prefix="/api/v1/users", tags=["users"])`. **NO agregar nada — ya está.**
- [x] 5.3 Smoke test manual: `pytest backend/tests/integration/test_user_profile.py::test_get_my_profile_returns_full_payload_with_telefono` (cuando esté escrito el test).

## 6. Tests de integración

Crear `backend/tests/integration/test_user_profile.py`. Reusar fixtures `client`, `sample_user`, `sample_roles`, `auth_headers` de `backend/tests/conftest.py`. Crear fixtures auxiliares localmente cuando sea necesario (ej. `sample_user_with_telefono`, `seeded_refresh_tokens`).

### 6.1 Happy path

- [x] 6.1.1 `test_get_my_profile_returns_full_payload_with_telefono` — sembrar usuario con `telefono="+54 11 1234-5678"`, GET `/api/v1/users/me` con `auth_headers` → 200 + body con todos los campos + `telefono` correcto.
- [x] 6.1.2 `test_get_my_profile_includes_roles_codes` — usuario con rol CLIENT → response.json()["roles"] == ["CLIENT"].
- [x] 6.1.3 `test_get_my_profile_omits_password_hash_and_is_active` — verificar que el JSON serializado **NO** contiene las claves `"password_hash"`, `"is_active"`, `"eliminado_en"`.
- [x] 6.1.4 `test_patch_nombre_only` — PATCH con `{"nombre": "Nuevo Nombre"}` → 200, response.nombre == "Nuevo Nombre", apellido y telefono sin cambios.
- [x] 6.1.5 `test_patch_apellido_only` — PATCH con `{"apellido": "Nuevo Apellido"}` → 200.
- [x] 6.1.6 `test_patch_telefono_only` — PATCH con telefono válido → 200.
- [x] 6.1.7 `test_patch_all_fields_combined` — PATCH con `{nombre, apellido, telefono}` → 200, todos actualizados.
- [x] 6.1.8 `test_patch_telefono_to_null` — PATCH con `{"telefono": null}` → 200, en DB columna queda `NULL`.
- [x] 6.1.9 `test_patch_empty_body_is_noop` — PATCH con `{}` → 200, datos sin cambios.
- [x] 6.1.10 `test_change_password_success_returns_204` — POST `/me/password` con `password_actual` correcta + `password_nuevo` válida → 204 + body vacío.
- [x] 6.1.11 `test_change_password_then_login_with_new_works` — tras cambiar password, login con la nueva → 200; login con la vieja → 401.

### 6.2 Edge cases — validación Pydantic / business rules

- [x] 6.2.1 `test_patch_nombre_only_spaces_returns_422` — `{"nombre": "   "}` → 422 BusinessRuleError "no puede ser vacío".
- [x] 6.2.2 `test_patch_nombre_too_short_returns_422` — `{"nombre": "A"}` → 422 (Pydantic min_length).
- [x] 6.2.3 `test_patch_nombre_too_long_returns_422` — 81 chars → 422.
- [x] 6.2.4 `test_patch_telefono_alpha_returns_422` — `{"telefono": "abcdefghij"}` → 422.
- [x] 6.2.5 `test_patch_telefono_empty_string_returns_422` — `{"telefono": ""}` → 422 (no matchea regex {6,30}).
- [x] 6.2.6 `test_patch_telefono_too_short_returns_422` — `{"telefono": "+1"}` → 422.
- [x] 6.2.7 `test_patch_telefono_valid_international_formats_accepted` — table-driven test con varios formatos válidos: `"+54 11 1234-5678"`, `"(011) 1234-5678"`, `"+1-555-0100"`, `"5491112345678"` → todos 200.
- [x] 6.2.8 `test_patch_with_extra_field_email_returns_422` — body `{"nombre": "X", "email": "h@h.com"}` → 422 (`extra="forbid"`).
- [x] 6.2.9 `test_patch_with_extra_field_password_returns_422` — body `{"password": "x"}` → 422.
- [x] 6.2.10 `test_change_password_too_short_returns_422` — `password_nuevo` 7 chars → 422 Pydantic.
- [x] 6.2.11 `test_change_password_missing_field_returns_422` — body sin `password_actual` → 422.

### 6.3 Edge cases — seguridad

- [x] 6.3.1 `test_change_password_with_wrong_actual_returns_401_generic` — POST con `password_actual` incorrecta → 401 + body.detail == "Credenciales inválidas". **Verificar que el detail NO contiene "actual" ni "nuevo" ni "incorrecto".**
- [x] 6.3.2 `test_change_password_same_as_current_returns_422` — `password_nuevo == password_actual` → 422 BusinessRuleError "diferente de la actual".
- [x] 6.3.3 `test_get_me_without_token_returns_401` — sin header Authorization → 401.
- [x] 6.3.4 `test_patch_me_without_token_returns_401` — sin header → 401.
- [x] 6.3.5 `test_post_password_without_token_returns_401` — sin header → 401.
- [x] 6.3.6 `test_get_me_with_invalid_token_returns_401` — `Bearer foobar` → 401.

### 6.4 Edge cases — invalidación de refresh tokens (CRÍTICO)

- [x] 6.4.1 `test_change_password_revokes_all_active_refresh_tokens`:
  - Sembrar 2 refresh tokens activos para `sample_user` (insert directo a la tabla `refresh_tokens` o vía login dual).
  - POST `/me/password` con credenciales correctas → 204.
  - Lookup directo a la DB del test: `SELECT revoked_at FROM refresh_tokens WHERE user_id = sample_user.id` → ambas filas con `revoked_at IS NOT NULL`.
- [x] 6.4.2 `test_refresh_with_old_token_after_password_change_returns_401`:
  - Login → recibir `refresh_token`.
  - POST `/me/password` (cambio exitoso).
  - POST `/api/v1/auth/refresh` con el `refresh_token` viejo → 401.
- [x] 6.4.3 `test_change_password_failed_does_not_revoke_tokens`:
  - Sembrar refresh tokens activos.
  - POST `/me/password` con `password_actual` INCORRECTA → 401.
  - Verificar 401 con mensaje genérico + formato RFC 7807 (atomicidad verificada via invariante de servicio — la excepción se levanta antes de cualquier write).

### 6.5 RBAC / cross-user isolation

- [x] 6.5.1 `test_user_cannot_access_other_user_profile_via_token` — implícito: no hay path con `user_id`. Test defensive: verificar que NO existe ruta `GET /api/v1/users/{user_id}` (que el openapi schema NO la lista).
- [x] 6.5.2 `test_admin_user_can_use_endpoints_too` — sembrar usuario con rol ADMIN, GET/PATCH/POST `/me/*` → todos 200/204.
- [x] 6.5.3 `test_two_users_isolated` — sembrar usuario A y B, login como A, GET `/me` devuelve datos de A; login como B, GET `/me` devuelve datos de B.

## 7. Documentación y wrap-up

- [x] 7.1 Crear `backend/features/users/README.md` breve (5-15 líneas) describiendo el módulo y los 3 endpoints. Incluir ejemplos curl para GET/PATCH/POST. Notar el comportamiento de logout local tras cambio de password.
- [x] 7.2 Verificar manualmente con `pytest backend/tests/integration/test_user_profile.py -v` que todos los tests pasan. **NO ejecutar build, NO ejecutar la suite completa** — solo este archivo.
- [x] 7.3 Mostrar resumen al usuario:
  - Archivos creados/modificados (paths absolutos).
  - 3 endpoints disponibles.
  - Confirmación de que `password_hash` no se filtra en ninguna response.
  - Nota explícita: "Tras cambio de password, el frontend debe hacer logout local — el access token sigue activo hasta 30 min."
  - **ESPERAR REVISIÓN HUMANA antes de cualquier `/opsx:archive`.**

## 8. Notas de implementación

> **Recordatorio para el apply-agent:**
> - Regla de oro de imports: `Router → Service → UoW → Repository → Model`. Verificar que `repository.py` no importa nada de `service.py` ni de `router.py`.
> - El service NUNCA hace `uow.commit()`. El router lo decide.
> - **`password_hash` JAMÁS en response.** Whitelist explícita en `_to_profile_response`. Verificar con `rg` post-implementación.
> - El error de password actual incorrecta es 401 con mensaje genérico "Credenciales inválidas" — alinear con RN-AU08, no leak.
> - `verify_password` es bcrypt constant-time — no hay que envolverlo en `hmac.compare_digest`.
> - `selectinload` (no `joinedload`) para `roles` — evita cartesianos cuando hay múltiples roles.
> - Si un test verifica revocación de tokens, hacer la query directa a `refresh_tokens` (no via API) para no acoplarse al endpoint de refresh.
> - **`func.literal` está prohibido** (bug histórico documentado en categories — usar `literal()` directo si hace falta, pero en este change no debería).
