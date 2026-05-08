## 1. Migración Alembic — agregar `piso_depto`

> **Esta task DEBE completarse PRIMERO.** Las tasks 2-7 dependen del esquema actualizado.

- [x] 1.1 Crear archivo `backend/alembic/versions/20260508_0002_piso_depto_to_delivery_addresses.py` siguiendo el patrón EXACTO de `20260508_0001_es_removible_to_product_ingredients.py`. **NO usar `alembic revision --autogenerate`** — Postgres no corre en el ambiente del apply-agent.
- [x] 1.2 En el archivo, definir:
  - `revision: str = "piso_depto_delivery_addresses"`.
  - `down_revision: Union[str, None] = "es_removible_product_ingredients"` (head actual; verificable con `eza backend/alembic/versions/`).
  - `branch_labels: Union[str, Sequence[str], None] = None`.
  - `depends_on: Union[str, Sequence[str], None] = None`.
- [x] 1.3 Implementar `def upgrade() -> None`:
  - `op.add_column("delivery_addresses", sa.Column("piso_depto", sa.String(length=50), nullable=True))`.
  - Docstring: "Add piso_depto column to delivery_addresses (nullable, no default)."
  - **NO** agregar `server_default` — la columna es opcional desde el día 0.
- [x] 1.4 Implementar `def downgrade() -> None`:
  - `op.drop_column("delivery_addresses", "piso_depto")`.
  - Docstring: "Remove piso_depto column from delivery_addresses."
- [x] 1.5 Verificar con `rg "piso_depto" backend/alembic/versions/` → 1 match (solo este archivo nuevo).
- [x] 1.6 **NO ejecutar `alembic upgrade head`** desde el apply-agent — el usuario lo correrá manualmente con su Postgres local antes de hacer review.

## 2. Modelo ORM — agregar `piso_depto` a `DireccionEntrega`

- [x] 2.1 Editar `backend/features/addresses/models.py`. La importación `Optional` de `typing` ya está presente (línea 11) — reutilizar.
- [x] 2.2 Insertar el campo `piso_depto` entre `numero` y `ciudad` para mantener orden lógico de spec:
  ```python
  piso_depto: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  ```
- [x] 2.3 Verificar con `rg "piso_depto" backend/features/addresses/models.py` → 1 match.
- [x] 2.4 Verificar con `rg "piso_depto" backend/features/addresses/` que NO existen otras referencias previas que pudieran confundir.

## 3. Schemas Pydantic v2 (`schemas.py`)

- [x] 3.1 Crear `backend/features/addresses/schemas.py` con docstring inicial:
  ```
  """
  Pydantic v2 schemas for delivery addresses CRUD.
  Three schemas: DireccionCreate, DireccionUpdate, DireccionRead.
  """
  ```
- [x] 3.2 Importar `from __future__ import annotations`, `BaseModel`, `Field` de `pydantic`, `datetime` de `datetime`.
- [x] 3.3 Definir `DireccionCreate(BaseModel)` con todos los campos del modelo MENOS `id`, `usuario_id`/`user_id`, `es_principal`, `creado_en`, `actualizado_en`, `eliminado_en`:
  - `calle: str = Field(..., min_length=1, max_length=255)`
  - `numero: str = Field(..., min_length=1, max_length=20)`
  - `piso_depto: str | None = Field(None, max_length=50)`
  - `ciudad: str = Field(..., min_length=1, max_length=100)`
  - `codigo_postal: str = Field(..., min_length=1, max_length=20)`
  - `referencia: str | None = Field(None, max_length=500)`
  - `model_config = {"extra": "forbid"}`.
  - Docstring: "Create payload. `es_principal` and `usuario_id` are NEVER accepted (anti-smuggling, D3/D6)."
- [x] 3.4 Definir `DireccionUpdate(BaseModel)` con TODOS los campos opcionales (con la misma validación) + `model_config = {"extra": "forbid"}`. Docstring: "All fields optional. The service uses `model_dump(exclude_unset=True)`. `es_principal` is NEVER accepted (use PATCH /predeterminada instead)."
- [x] 3.5 Definir `DireccionRead(BaseModel)`:
  - `id: int`, `usuario_id: int`, `calle: str`, `numero: str`, `piso_depto: str | None`, `ciudad: str`, `codigo_postal: str`, `referencia: str | None`, `es_principal: bool`, `creado_en: datetime`, `actualizado_en: datetime`.
  - `model_config = {"from_attributes": True}`.
  - Para mapear `user_id` (modelo) → `usuario_id` (schema): usar `from pydantic import Field` con `usuario_id: int = Field(..., validation_alias="user_id")`. Verificar que `model_validate` funciona con `from_attributes` + `validation_alias` en Pydantic v2.
  - Docstring: "Public representation. `usuario_id` is aliased from `user_id` to match spec naming."
- [x] 3.6 Verificar con `rg "es_principal" backend/features/addresses/schemas.py` → solo aparece en `DireccionRead`, NO en `DireccionCreate` ni `DireccionUpdate`.
- [x] 3.7 Verificar con `rg "user_id|usuario_id" backend/features/addresses/schemas.py` → solo en `DireccionRead`, NO en Create/Update (anti-smuggling).

## 4. Repository (`repository.py`)

- [x] 4.1 Crear `backend/features/addresses/repository.py` con docstring inicial.
- [x] 4.2 Importar `from __future__ import annotations`, `Optional` de `typing`, `select`, `update`, `func` de `sqlalchemy`, `Session` de `sqlalchemy.orm`, `DireccionEntrega` de `backend.features.addresses.models`, `BaseRepository` de `backend.shared.repository`.
- [x] 4.3 Crear `class AddressRepository(BaseRepository[DireccionEntrega])`:
  - `def __init__(self, session: Session) -> None: super().__init__(session, DireccionEntrega)`.
- [x] 4.4 Implementar `find_by_id_and_user(self, address_id: int, user_id: int) -> Optional[DireccionEntrega]`:
  - Construir query: `self._get_base_query().where(DireccionEntrega.id == address_id).where(DireccionEntrega.user_id == user_id)`.
  - Retornar `self.session.execute(query).scalar_one_or_none()`.
  - Docstring: "Return the address only if it belongs to user_id AND is active. Single source of truth for ownership enforcement (D6)."
- [x] 4.5 Implementar `list_active_by_user(self, user_id: int) -> list[DireccionEntrega]`:
  - Query con `_get_base_query()`, filtrado por `user_id`, `order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.id.asc())`.
  - Retornar `list(self.session.execute(query).scalars().all())`.
- [x] 4.6 Implementar `count_active_by_user(self, user_id: int) -> int`:
  - `base = self._get_base_query().where(DireccionEntrega.user_id == user_id)`.
  - `count_query = select(func.count()).select_from(base.subquery())`.
  - Retornar `self.session.execute(count_query).scalar() or 0`.
- [x] 4.7 Implementar `find_principal_by_user(self, user_id: int) -> Optional[DireccionEntrega]`:
  - Query con `_get_base_query()`, filtrado por `user_id` y `es_principal.is_(True)`.
  - Retornar `scalar_one_or_none()`.
  - Docstring: "Helper for tests / defensive checks. NOT used in the swap path."
- [x] 4.8 Implementar `unset_principal_for_user(self, user_id: int) -> None`:
  - Construir bulk UPDATE: `update(DireccionEntrega).where(user_id == X).where(eliminado_en IS NULL).where(es_principal IS True).values(es_principal=False)`.
  - `self.session.execute(stmt)`. NO retornar nada (None).
  - Docstring: "Bulk UPDATE. Does NOT call session.flush() — leaves ordering to caller."
- [x] 4.9 Verificar con `rg "uow|UnitOfWork|service|router" backend/features/addresses/repository.py` → 0 matches (regla de oro de imports).
- [x] 4.10 Verificar con `rg "raise HTTPException" backend/features/addresses/repository.py` → 0 matches.

## 5. Service (`service.py`)

- [x] 5.1 Crear `backend/features/addresses/service.py` con docstring inicial.
- [x] 5.2 Importar `DireccionEntrega`, `AddressRepository`, `DireccionCreate`, `DireccionUpdate`, `BusinessRuleError`, `NotFoundError`, `UnitOfWork`.
- [x] 5.3 Crear `class AddressService` con `__init__(self, uow: UnitOfWork)` que:
  - `self.uow = uow`.
  - `uow.register_repository("direcciones", AddressRepository(uow.session))`.
- [x] 5.4 Implementar `create(self, user_id: int, payload: DireccionCreate) -> DireccionEntrega`:
  - `data = payload.model_dump(exclude_unset=True)`.
  - Para cada `key in ("calle", "numero", "ciudad", "codigo_postal")` que esté en `data`: aplicar `.strip()`. Si queda vacío → `raise BusinessRuleError(f"El campo {key} no puede ser vacío")`.
  - Para cada `key in ("piso_depto", "referencia")` que esté en `data` y no sea `None`: `data[key] = data[key].strip() or None`.
  - `is_first = self.uow.direcciones.count_active_by_user(user_id) == 0`.
  - `return self.uow.direcciones.create(user_id=user_id, es_principal=is_first, **data)`.
  - Docstring referenciar D3, RN-DI01.
- [x] 5.5 Implementar `list_for_user(self, user_id: int) -> list[DireccionEntrega]`:
  - `return self.uow.direcciones.list_active_by_user(user_id)`.
- [x] 5.6 Implementar `update(self, user_id: int, address_id: int, payload: DireccionUpdate) -> DireccionEntrega`:
  - `address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)`.
  - Si `address is None` → `raise NotFoundError("Dirección no encontrada")`.
  - `data = payload.model_dump(exclude_unset=True)`. Si vacío → `return address` (no-op).
  - Trim required strings (mismo bloque que en `create`). Trim optionals (mismo bloque).
  - `return self.uow.direcciones.update(address_id, **data)`.
- [x] 5.7 Implementar `delete(self, user_id: int, address_id: int) -> None`:
  - `address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)`.
  - Si `None` → `NotFoundError`.
  - `self.uow.direcciones.delete(address_id)` (heredado de BaseRepository — soft delete).
  - **NO** validar `es_principal` (D5: borrar la principal está permitido).
  - **NO** auto-promocionar otra dirección (D5).
- [x] 5.8 Implementar `set_principal(self, user_id: int, address_id: int) -> DireccionEntrega`:
  - `address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)`.
  - Si `None` → `NotFoundError`.
  - `self.uow.direcciones.unset_principal_for_user(user_id)`.
  - `address.es_principal = True`.
  - `return address`. **NO** llamar `flush()` ni `commit()`.
- [x] 5.9 Verificar con `rg "uow.commit\(\)|session.commit\(\)" backend/features/addresses/service.py` → 0 matches (D6).
- [x] 5.10 Verificar con `rg "fastapi|HTTPException" backend/features/addresses/service.py` → 0 matches (regla de oro de imports).

## 6. Router (`router.py`)

- [x] 6.1 Crear `backend/features/addresses/router.py` con docstring inicial mencionando los 5 endpoints + ownership por D6.
- [x] 6.2 Importar `from __future__ import annotations`, `APIRouter`, `Depends`, `Response`, `status` de `fastapi`; `get_uow` de `backend.dependencies`; `DireccionCreate`, `DireccionRead`, `DireccionUpdate` de `backend.features.addresses.schemas`; `AddressService` de `backend.features.addresses.service`; `get_current_user` de `backend.features.auth.dependencies`; `Usuario` de `backend.features.users.models`; `UnitOfWork` de `backend.shared.unit_of_work`.
- [x] 6.3 `router = APIRouter()` (sin prefix — se aplica en `main.py`).
- [x] 6.4 Implementar `POST /` con `status_code=status.HTTP_201_CREATED`, `response_model=DireccionRead`:
  - Params: `payload: DireccionCreate`, `current_user: Usuario = Depends(get_current_user)`, `uow: UnitOfWork = Depends(get_uow)`.
  - Lógica: `service = AddressService(uow); address = service.create(current_user.id, payload); uow.commit(); return DireccionRead.model_validate(address)`.
  - Summary: "Create a new delivery address (auto-marks principal if first)".
- [x] 6.5 Implementar `GET /` con `response_model=list[DireccionRead]`:
  - Params: `current_user`, `uow` (NO `payload`).
  - Lógica: `service.list_for_user(current_user.id)` → list comprehension `[DireccionRead.model_validate(a) for a in addresses]`.
  - **NO commit** (read-only).
- [x] 6.6 Implementar `PUT /{address_id}` con `response_model=DireccionRead`:
  - Params: `address_id: int` en path, `payload: DireccionUpdate`, `current_user`, `uow`.
  - Lógica: `service.update(current_user.id, address_id, payload); uow.commit(); return DireccionRead.model_validate(address)`.
- [x] 6.7 Implementar `DELETE /{address_id}` con `status_code=status.HTTP_204_NO_CONTENT`:
  - Params: `address_id: int`, `current_user`, `uow`.
  - Lógica: `service.delete(current_user.id, address_id); uow.commit(); return Response(status_code=204)`.
- [x] 6.8 Implementar `PATCH /{address_id}/predeterminada` con `response_model=DireccionRead`:
  - Params: `address_id: int`, `current_user`, `uow`.
  - Lógica: `address = service.set_principal(current_user.id, address_id); uow.commit(); return DireccionRead.model_validate(address)`.
- [x] 6.9 Verificar con `rg "raise HTTPException" backend/features/addresses/router.py` → 0 matches.
- [x] 6.10 Verificar con `rg "user_id" backend/features/addresses/router.py` → solo aparece como `current_user.id`, NUNCA como path param o body field.
- [x] 6.11 Verificar con `rg "require_role" backend/features/addresses/router.py` → 0 matches (no se requieren roles específicos, solo autenticación).

## 7. Wiring en `backend/main.py`

- [x] 7.1 Verificar que `backend/main.py:61` ya tiene `from backend.features.addresses import models as _address_models  # noqa: F401`. **NO modificar** — ya está.
- [x] 7.2 Agregar import del router después de los otros imports de feature routers (alrededor de la línea 72):
  ```python
  from backend.features.addresses.router import router as addresses_router
  ```
- [x] 7.3 Agregar `app.include_router(addresses_router, prefix="/api/v1/direcciones", tags=["addresses"])` después de los otros `include_router` (alrededor de la línea 201, manteniendo el orden alfabético-funcional del archivo). El prefix `/api/v1/direcciones` es **top-level** (D1), NO sub-path de `/users/me`.
- [x] 7.4 Smoke test manual con `pytest backend/tests/integration/test_delivery_addresses.py::test_create_address_returns_201_with_full_payload -v` (cuando exista el archivo de tests).

## 8. Tests de integración (`backend/tests/integration/test_delivery_addresses.py`)

Crear el archivo siguiendo el patrón de `test_user_profile.py` (auth + ownership-via-JWT) y `test_ingredients.py` (CRUD plano). Reusar fixtures `client`, `sample_user`, `auth_headers` de `backend/tests/conftest.py`. Crear fixtures locales auxiliares cuando sea necesario.

### 8.1 Happy path (10 tests)

- [x] 8.1.1 `test_create_address_returns_201_with_full_payload` — POST con todos los campos válidos → 201, response tiene id, usuario_id == sample_user.id, es_principal True (porque es la 1ra), creado_en/actualizado_en presentes.
- [x] 8.1.2 `test_create_first_address_auto_marks_as_principal` — usuario sin direcciones, POST → response.es_principal == True.
- [x] 8.1.3 `test_create_second_address_does_not_auto_mark` — usuario con 1 dirección principal previa, POST otra → response.es_principal == False.
- [x] 8.1.4 `test_create_with_optional_fields_omitted` — POST sin `piso_depto` ni `referencia` → 201, ambos en response son `null`.
- [x] 8.1.5 `test_create_trims_whitespace_in_required_fields` — POST con `{"calle": "  Av Siempre Viva  ", ...}` → 201, response.calle == "Av Siempre Viva".
- [x] 8.1.6 `test_list_addresses_returns_only_own` — sembrar 2 direcciones para sample_user y 1 para second_user; GET con auth de sample_user → exactamente 2 elementos, ninguno es de second_user.
- [x] 8.1.7 `test_list_addresses_principal_first` — sembrar addrA(no-principal, id menor) y addrB(principal, id mayor); GET → primer elemento es addrB.
- [x] 8.1.8 `test_update_address_partial` — PUT con solo `{"calle": "Nueva Calle"}` → 200, calle cambia, numero/ciudad/codigo_postal/referencia preservados, es_principal preservado.
- [x] 8.1.9 `test_update_clear_optional_field_with_null` — sembrar addr con `referencia="X"`; PUT con `{"referencia": null}` → 200, response.referencia == null AND DB column IS NULL.
- [x] 8.1.10 `test_set_principal_returns_200_with_updated_address` — sembrar addrA y addrB(principal); PATCH `/addrA/predeterminada` → 200, response.es_principal == True.

### 8.2 Ownership cross-user (CRÍTICO — D6, 6 tests)

- [x] 8.2.1 `test_get_list_excludes_other_users_addresses` — sembrar dirección para second_user; sample_user llama GET / → la dirección de second_user NO aparece.
- [x] 8.2.2 `test_update_other_user_address_returns_404` — sample_user hace PUT al id de una dirección de second_user → 404 con detail genérico.
- [x] 8.2.3 `test_delete_other_user_address_returns_404` — sample_user hace DELETE al id de second_user → 404, la dirección de second_user NO se borra (verificar con query directa).
- [x] 8.2.4 `test_set_principal_other_user_address_returns_404` — sample_user hace PATCH `/{id_de_second_user}/predeterminada` → 404; la dirección de second_user mantiene su estado.
- [x] 8.2.5 `test_404_detail_does_not_leak_ownership` — invocar uno de los tests anteriores y verificar que `body.detail` NO contiene las substrings `"ajena"`, `"propietario"`, `"forbidden"`, `"permission"` (case-insensitive).
- [x] 8.2.6 `test_404_for_nonexistent_id_same_response_as_foreign_id` — comparar response de PUT `/999999` (no existe) vs PUT `/{id_de_second_user}` → ambos 404 con el mismo detail genérico (anti-leak).

### 8.3 Atomicidad de PATCH /predeterminada (CRÍTICO — Risk #1, 3 tests)

- [x] 8.3.1 `test_set_principal_unsets_previous_principal` — sembrar addrA(principal) y addrB; PATCH `/addrB/predeterminada` → 200; query directa a DB verifica `addrA.es_principal == False AND addrB.es_principal == True`.
- [x] 8.3.2 `test_set_principal_idempotent` — sembrar addrA(principal); PATCH `/addrA/predeterminada` → 200, addrA.es_principal sigue True (sin error, sin doble unset).
- [x] 8.3.3 `test_set_principal_when_user_has_no_principal` — sembrar addrA y addrB ambas con `es_principal=False` (escenario post-borrado); PATCH `/addrA/predeterminada` → 200, addrA queda principal, addrB sigue no-principal.

### 8.4 Borrar la principal (D5, 3 tests)

- [x] 8.4.1 `test_delete_principal_returns_204` — sembrar addrA(principal); DELETE addrA → 204 (sin error pese a ser principal).
- [x] 8.4.2 `test_delete_principal_leaves_user_without_principal` — sembrar addrA(principal) y addrB(no-principal); DELETE addrA → query directa: addrB.es_principal sigue False (NO auto-promoción).
- [x] 8.4.3 `test_after_delete_only_principal_next_create_is_auto_principal` — sembrar SOLO addrA(principal); DELETE addrA → POST nueva addrC → addrC.es_principal == True (count_active vuelve a 0 → D3).

### 8.5 Anti-smuggling (CRÍTICO — Risk #4, 4 tests)

- [x] 8.5.1 `test_create_with_es_principal_in_body_returns_422` — POST con `{"calle": ..., "es_principal": true}` → 422 con detail listando `es_principal` como extra forbidden field.
- [x] 8.5.2 `test_create_with_usuario_id_in_body_returns_422` — POST con `{"calle": ..., "usuario_id": 999}` → 422.
- [x] 8.5.3 `test_update_with_es_principal_in_body_returns_422` — PUT con `{"es_principal": true}` → 422 (la única manera legítima es PATCH /predeterminada).
- [x] 8.5.4 `test_update_with_unknown_field_returns_422` — PUT con `{"foo": "bar"}` → 422.

### 8.6 Validación Pydantic / business rules (5 tests)

- [x] 8.6.1 `test_create_with_empty_calle_returns_422` — POST con `{"calle": ""}` → 422 (Pydantic min_length=1).
- [x] 8.6.2 `test_create_with_whitespace_only_calle_returns_422` — POST con `{"calle": "   "}` → 422 BusinessRuleError "no puede ser vacío".
- [x] 8.6.3 `test_create_with_calle_too_long_returns_422` — calle de 256 chars → 422.
- [x] 8.6.4 `test_create_missing_required_field_returns_422` — POST sin `numero` → 422 (Pydantic missing).
- [x] 8.6.5 `test_create_with_piso_depto_too_long_returns_422` — `piso_depto` de 51 chars → 422.

### 8.7 Soft delete (2 tests)

- [x] 8.7.1 `test_delete_address_soft_returns_204` — DELETE → 204; query directa: la fila existe con `eliminado_en IS NOT NULL` (NO se borra físicamente, RN-CA09).
- [x] 8.7.2 `test_deleted_address_does_not_appear_in_list` — sembrar addrA + addrB, DELETE addrA, GET / → solo addrB en response.

### 8.8 Auth (3 tests)

- [x] 8.8.1 `test_endpoints_without_token_return_401` — table-driven: POST/GET/PUT/DELETE/PATCH sin Authorization header → todos 401.
- [x] 8.8.2 `test_endpoints_with_invalid_token_return_401` — POST con `Authorization: Bearer foobar` → 401.
- [x] 8.8.3 `test_admin_user_uses_endpoints_too` — usuario con rol ADMIN puede usar todos los endpoints sobre sus propias direcciones (cualquier rol autenticado).

## 9. Documentación y wrap-up

- [x] 9.1 Crear `backend/features/addresses/README.md` breve (10-20 líneas):
  - Descripción del módulo (1-2 oraciones).
  - Lista de los 5 endpoints con método + path + 1 línea de propósito.
  - Ejemplo curl para POST /api/v1/direcciones (con header Bearer y body completo).
  - Nota sobre RN-DI01 (auto-principal en primera) y D6 (404 anti-leak).
- [x] 9.2 Verificar que `rg "addresses_router" backend/main.py` devuelve 2 matches (1 import + 1 include_router).
- [x] 9.3 Verificar manualmente con `pytest backend/tests/integration/test_delivery_addresses.py -v` que todos los tests pasan. **NO ejecutar build, NO ejecutar la suite completa** — solo este archivo.
- [x] 9.4 Mostrar resumen al usuario:
  - Archivos creados/modificados (paths absolutos).
  - 5 endpoints disponibles con sus métodos y URLs completas.
  - Recordatorio: el usuario DEBE correr `alembic upgrade head` en su Postgres local antes de que el backend pueda aceptar requests sobre `/api/v1/direcciones` (sino la columna `piso_depto` no existe).
  - **ESPERAR REVISIÓN HUMANA antes de cualquier `/opsx:archive`.**

## 10. Notas de implementación

> **Recordatorio para el apply-agent:**
> - **Regla de oro de imports**: `Router → Service → UoW → Repository → Model`. Verificar que `repository.py` no importa nada de `service.py` ni de `router.py`, y que `service.py` no importa `fastapi`.
> - **Service NUNCA hace `uow.commit()`** — el router lo decide.
> - **Ownership por 404, NO 403** (D6) — `find_by_id_and_user` devuelve `None` para "no existe" y "ajena", el service levanta `NotFoundError` en ambos casos. El detail SIEMPRE genérico ("Dirección no encontrada"), nunca menciona "ajena" ni "permisos".
> - **`extra="forbid"` en Create y Update** — anti-smuggling de `es_principal` y `usuario_id`. Auditar con `rg "es_principal|user_id|usuario_id" backend/features/addresses/schemas.py` → solo en `DireccionRead`.
> - **`es_principal` solo se cambia vía PATCH /predeterminada** — NUNCA via POST ni PUT.
> - **NO `func.literal`** (bug histórico documentado en categories) — usar `literal()` directo si hace falta, pero en este change no debería ser necesario.
> - **NO `--autogenerate` para la migración** — escribir a mano siguiendo `20260508_0001_es_removible_to_product_ingredients.py`.
> - **NO ejecutar `alembic upgrade head`** desde el apply-agent — el usuario lo correrá manualmente.
> - **NO ejecutar la suite completa de tests** — solo `test_delivery_addresses.py`.
> - **NO commitear** los cambios — el usuario decide cuándo commitear.
> - **NO archivar** el change — el usuario revisa y luego ejecuta `/opsx:archive`.
