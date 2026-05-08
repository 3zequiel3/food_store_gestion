# Design: delivery-addresses-backend

## 0. Contexto y alcance

Change #13 del roadmap (`docs/CHANGES.md:118-123`), segundo y último change del Sprint 4 (Perfil y Direcciones — Backend). Incluye exactamente **5 endpoints REST** bajo `/api/v1/direcciones`, una **migración Alembic nueva** para agregar la columna `piso_depto`, y reusa al máximo la infraestructura ya consolidada por `users/`, `categories/`, `ingredients/` y `products/`.

**Reusos no negociables (NO redefinir):**
- Modelo: `DireccionEntrega` en `backend/features/addresses/models.py:19-50` (extender con `piso_depto`, no recrear).
- Auth dep: `get_current_user` en `backend/features/auth/dependencies.py:27`.
- Excepciones: `NotFoundError`, `BusinessRuleError`, `UnauthorizedError` en `backend/shared/exceptions.py` (handlers RFC 7807 ya registrados en `backend/main.py:108-119`).
- UoW: `UnitOfWork` y `Depends(get_uow)` desde `backend/dependencies.py:20`.
- BaseRepository: `backend/shared/repository.py` ya post-fix (changes `fix-base-repository-soft-delete` y `fix-base-repository-immutable-fields` archivados — heredar sin overrides defensivos).

**Out of scope (registrado en proposal):**
- Validar pedidos activos antes de DELETE (US-027) → Sprint 5 cuando exista `orders` con datos.
- Geocoding / lat-lng.
- Endpoint admin sobre direcciones de otros usuarios (va en `admin-users-backend` #18).
- `GET /api/v1/direcciones/{id}` individual — ninguna US lo requiere.
- Auto-promoción de otra dirección al borrar la principal — D5 explícito.

## 1. Estructura del módulo

El módulo `backend/features/addresses/` ya existe como stub:

```
backend/features/addresses/
├── __init__.py          (vacío — dejar tal cual)
├── models.py            (COMPLETO — DireccionEntrega — agregar SOLO piso_depto)
├── repository.py        (NUEVO — AddressRepository)
├── schemas.py           (NUEVO — DireccionCreate/Update/Read)
├── service.py           (NUEVO — AddressService)
├── router.py            (NUEVO — 5 endpoints)
└── README.md            (NUEVO — breve descripción + curl examples)
```

`backend/main.py:61` ya importa `_address_models` para el registry SQLAlchemy. Falta:
1. Importar `from backend.features.addresses.router import router as addresses_router`.
2. Montar `app.include_router(addresses_router, prefix="/api/v1/direcciones", tags=["addresses"])`.

**Regla de oro de imports** (estricta — auditada en review):
```
router.py → service.py → unit_of_work.py → repository.py → models.py
```
`repository.py` NO importa de `service.py` ni de `router.py`. `service.py` NO importa FastAPI ni schemas Pydantic como tipos de retorno (el router serializa con `model_validate`).

## 2. Modelo `DireccionEntrega` — extensión con `piso_depto`

### Estado actual (`backend/features/addresses/models.py:19-50`)

```python
class DireccionEntrega(BaseModel):
    __tablename__ = "delivery_addresses"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    calle: Mapped[str] = mapped_column(String(255), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_postal: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # creado_en, actualizado_en, eliminado_en heredados de BaseModel
```

### Cambio (D9): agregar `piso_depto`

Justificación: US-024 (línea 977 de `docs/Historias_de_usuario.txt`) lista textualmente "calle, numero, **piso/depto (opcional)**, ciudad, codigo postal" como campos de la dirección. El modelo actual no tiene un campo dedicado — la opción "usar `referencia` para absorber piso/depto" mezcla dos semánticas (instrucciones de entrega vs. unidad del edificio). Agregar `piso_depto` mantiene `referencia` libre para landmarks ("portón rojo, frente al kiosco").

Diff a aplicar:

```python
piso_depto: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

Posicionar entre `numero` y `ciudad` para mantener orden lógico de spec.

## 3. Migración Alembic nueva (`add_piso_depto_to_delivery_addresses`)

### Por qué una migración nueva (no `--autogenerate`)

Postgres no corre en el ambiente del apply-agent — `alembic revision --autogenerate` requiere comparar el modelo contra una base viva. La migración se escribe **a mano** siguiendo el patrón ya validado en `backend/alembic/versions/20260508_0001_es_removible_to_product_ingredients.py` (la última migración de feature del proyecto).

### Archivo a crear

Path: `backend/alembic/versions/20260508_0002_piso_depto_to_delivery_addresses.py` (timestamp `20260508_0002` para mantener orden lexicográfico tras la migración `20260508_0001` de `es_removible`).

```python
"""add piso_depto to delivery_addresses

Revision ID: piso_depto_delivery_addresses
Revises: es_removible_product_ingredients
Create Date: 2026-05-08 00:02:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "piso_depto_delivery_addresses"
down_revision: Union[str, None] = "es_removible_product_ingredients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add piso_depto column to delivery_addresses (nullable, no default)."""
    op.add_column(
        "delivery_addresses",
        sa.Column("piso_depto", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Remove piso_depto column from delivery_addresses."""
    op.drop_column("delivery_addresses", "piso_depto")
```

Notas críticas:
- **`down_revision = "es_removible_product_ingredients"`** — la head actual de la cadena Alembic (verificable con `eza backend/alembic/versions/`).
- `nullable=True` sin `server_default` — al ser opcional desde el día 0, las filas existentes pueden tener `NULL`. Esto NO rompe ninguna constraint.
- La migración es reversible: `downgrade()` simplemente elimina la columna. Como la columna es nullable, el `drop_column` es seguro en cualquier ambiente.
- **NO requiere data migration** — no hay backfill de datos existentes.

## 4. Schemas Pydantic v2 (`schemas.py`)

### `DireccionCreate`

Body de `POST /api/v1/direcciones`. **`extra="forbid"`** rechaza intentos de smuggling de `es_principal` o `usuario_id`.

```python
class DireccionCreate(BaseModel):
    calle: str = Field(..., min_length=1, max_length=255)
    numero: str = Field(..., min_length=1, max_length=20)
    piso_depto: str | None = Field(None, max_length=50)
    ciudad: str = Field(..., min_length=1, max_length=100)
    codigo_postal: str = Field(..., min_length=1, max_length=20)
    referencia: str | None = Field(None, max_length=500)

    model_config = {"extra": "forbid"}
```

Notas:
- `es_principal` **NO se declara** — la determinación es responsabilidad del service (D3, RN-DI01).
- `usuario_id` **NO se declara** — sale del JWT vía `current_user.id`.
- `piso_depto`, `referencia` opcionales (US-024 dice "piso/depto (opcional)").
- `min_length=1` en los obligatorios bloquea strings vacíos. El service hace `.strip()` adicional para detectar `"   "`.

### `DireccionUpdate`

Body de `PUT /api/v1/direcciones/{id}`. **Todos los campos opcionales**, `extra="forbid"`.

```python
class DireccionUpdate(BaseModel):
    calle: str | None = Field(None, min_length=1, max_length=255)
    numero: str | None = Field(None, min_length=1, max_length=20)
    piso_depto: str | None = Field(None, max_length=50)
    ciudad: str | None = Field(None, min_length=1, max_length=100)
    codigo_postal: str | None = Field(None, min_length=1, max_length=20)
    referencia: str | None = Field(None, max_length=500)

    model_config = {"extra": "forbid"}
```

Notas:
- Para "limpiar" `piso_depto` o `referencia` el cliente envía `null` explícito → `model_dump(exclude_unset=True)` lo distingue de "no enviado".
- `es_principal` y `usuario_id` excluidos — el primero solo se cambia vía `PATCH /predeterminada`, el segundo nunca.

### `DireccionRead`

Response de POST/PUT/PATCH/GET. Whitelist explícita.

```python
class DireccionRead(BaseModel):
    id: int
    usuario_id: int                      # alias del campo `user_id` del modelo
    calle: str
    numero: str
    piso_depto: str | None
    ciudad: str
    codigo_postal: str
    referencia: str | None
    es_principal: bool
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}
```

Nota: el modelo usa `user_id` como nombre de columna; el schema lo expone como `usuario_id` para ser consistente con el lenguaje de spec (Integrador.txt §3.1 usa "Usuario" / "DireccionEntrega.usuario_id"). Implementación: declarar `usuario_id: int = Field(..., validation_alias="user_id")` o mapear explícitamente en un helper (decisión del apply-agent — ambas funcionan; preferir el helper si simplifica).

## 5. Repository (`repository.py`)

```python
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.features.addresses.models import DireccionEntrega
from backend.shared.repository import BaseRepository


class AddressRepository(BaseRepository[DireccionEntrega]):
    """Data access for DireccionEntrega.

    Inherits create/read/update/delete (soft delete)/list from BaseRepository.
    Adds methods specialised for ownership enforcement and principal-address
    bookkeeping.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)

    # ── Ownership enforcement (D6) ────────────────────────────────────────

    def find_by_id_and_user(
        self, address_id: int, user_id: int
    ) -> Optional[DireccionEntrega]:
        """Return the address only if it belongs to ``user_id`` AND is active.

        This is the SINGLE source of truth for ownership enforcement (RN-DI03):
        the service treats a None result as 'not found OR not yours' and raises
        NotFoundError → 404 (intentional, anti-leak — see Risk #5).
        """
        query = (
            self._get_base_query()  # filters eliminado_en IS NULL
            .where(DireccionEntrega.id == address_id)
            .where(DireccionEntrega.user_id == user_id)
        )
        return self.session.execute(query).scalar_one_or_none()

    # ── Per-user listing ──────────────────────────────────────────────────

    def list_active_by_user(self, user_id: int) -> list[DireccionEntrega]:
        """Return all active addresses of a user, principal first then by id."""
        query = (
            self._get_base_query()
            .where(DireccionEntrega.user_id == user_id)
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.id.asc())
        )
        return list(self.session.execute(query).scalars().all())

    def count_active_by_user(self, user_id: int) -> int:
        """Count active addresses of a user (used by service for D3 auto-mark)."""
        from sqlalchemy import func
        query = (
            select(func.count())
            .select_from(self._get_base_query().subquery())
        )
        # Need to re-build the base query with the user filter:
        base = (
            self._get_base_query()
            .where(DireccionEntrega.user_id == user_id)
        )
        count_query = select(func.count()).select_from(base.subquery())
        return self.session.execute(count_query).scalar() or 0

    def find_principal_by_user(
        self, user_id: int
    ) -> Optional[DireccionEntrega]:
        """Return the user's current principal address, if any.

        Helper for tests and defensive checks. NOT used in the swap path —
        the swap uses bulk UPDATE via unset_principal_for_user.
        """
        query = (
            self._get_base_query()
            .where(DireccionEntrega.user_id == user_id)
            .where(DireccionEntrega.es_principal.is_(True))
        )
        return self.session.execute(query).scalar_one_or_none()

    # ── Principal-flag bookkeeping ────────────────────────────────────────

    def unset_principal_for_user(self, user_id: int) -> None:
        """Bulk UPDATE: set es_principal=False for ALL active addresses of user.

        Used by the service inside the swap transaction:
          1. unset_principal_for_user(user_id)
          2. address.es_principal = True

        Both staged in the same UoW session — committed atomically by the
        router's uow.commit() (RN-DI02).

        IMPORTANT: this method does NOT call session.flush() — leaves ordering
        to the caller. The service can rely on SQLAlchemy's autoflush behaviour
        when the next read happens, or call session.flush() explicitly.
        """
        stmt = (
            update(DireccionEntrega)
            .where(DireccionEntrega.user_id == user_id)
            .where(DireccionEntrega.eliminado_en.is_(None))
            .where(DireccionEntrega.es_principal.is_(True))
            .values(es_principal=False)
        )
        self.session.execute(stmt)
```

Decisiones del repo:
- **`find_by_id_and_user` es la base de la D6**: combina existencia + ownership en una sola query. Service interpreta `None` como `NotFoundError`.
- `list_active_by_user` ordena `es_principal DESC, id ASC` — la principal aparece primera, mejorando UX del frontend que itera y resalta.
- `count_active_by_user` es la base de **D3** (auto-marcar primera) — usa el patrón `select(func.count()).select_from(base.subquery())` validado en `IngredientRepository.list_paginated`.
- `unset_principal_for_user` usa **bulk UPDATE** (no fetch + loop) para ser una sola sentencia SQL — no hay race window dentro de la transacción si el commit es único.

## 6. Service (`service.py`)

```python
from backend.features.addresses.models import DireccionEntrega
from backend.features.addresses.repository import AddressRepository
from backend.features.addresses.schemas import DireccionCreate, DireccionUpdate
from backend.shared.exceptions import BusinessRuleError, NotFoundError
from backend.shared.unit_of_work import UnitOfWork


class AddressService:
    """Self-service address management for authenticated users.

    Registered repository:
      - uow.direcciones → AddressRepository

    NEVER calls uow.commit() — the router decides the transaction boundary.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        uow.register_repository("direcciones", AddressRepository(uow.session))

    # ── Create (US-024, RN-DI01) ──────────────────────────────────────────

    def create(self, user_id: int, payload: DireccionCreate) -> DireccionEntrega:
        """Create a new address; auto-mark as principal if it's the user's first.

        D3 — auto-mark logic:
          if count_active_by_user(user_id) == 0 → es_principal = True
          else → es_principal = False (default).

        Raises:
            BusinessRuleError: if any non-empty string field collapses to ""
                after .strip() (defensive — Pydantic min_length=1 catches the
                most common cases but not '   ' with whitespace).
        """
        data = payload.model_dump(exclude_unset=True)
        # Trim required strings; reject post-trim empties
        for key in ("calle", "numero", "ciudad", "codigo_postal"):
            if key in data and data[key] is not None:
                data[key] = data[key].strip()
                if not data[key]:
                    raise BusinessRuleError(f"El campo {key} no puede ser vacío")
        # Trim optional strings; convert empty-after-trim to None (cleaner DB)
        for key in ("piso_depto", "referencia"):
            if key in data and data[key] is not None:
                data[key] = data[key].strip() or None

        is_first = self.uow.direcciones.count_active_by_user(user_id) == 0

        return self.uow.direcciones.create(
            user_id=user_id,
            es_principal=is_first,
            **data,
        )

    # ── List (US-025, RN-DI03) ────────────────────────────────────────────

    def list_for_user(self, user_id: int) -> list[DireccionEntrega]:
        """Return the user's active addresses, principal first."""
        return self.uow.direcciones.list_active_by_user(user_id)

    # ── Update (US-026, RN-DI03 / D6) ─────────────────────────────────────

    def update(
        self, user_id: int, address_id: int, payload: DireccionUpdate
    ) -> DireccionEntrega:
        """Partially update an address validating ownership.

        Ownership: find_by_id_and_user returns None for both 'does not exist'
        and 'belongs to another user'. We raise NotFoundError → 404 in BOTH
        cases (D6, anti-leak).
        """
        address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)
        if address is None:
            raise NotFoundError("Dirección no encontrada")

        data = payload.model_dump(exclude_unset=True)
        if not data:
            return address  # PATCH-style no-op

        # Trim non-null required strings; reject empties post-trim
        for key in ("calle", "numero", "ciudad", "codigo_postal"):
            if key in data and data[key] is not None:
                data[key] = data[key].strip()
                if not data[key]:
                    raise BusinessRuleError(f"El campo {key} no puede ser vacío")
        # Optional strings: collapse empty-after-trim to None
        for key in ("piso_depto", "referencia"):
            if key in data and data[key] is not None:
                data[key] = data[key].strip() or None

        return self.uow.direcciones.update(address_id, **data)

    # ── Delete (US-027, D5) ───────────────────────────────────────────────

    def delete(self, user_id: int, address_id: int) -> None:
        """Soft-delete an address validating ownership.

        Per D5: deleting the principal is allowed and leaves the user with NO
        principal. We do NOT auto-promote another address. The next create()
        will auto-mark by D3 (count goes back to 0 of active addresses... wait,
        unless the user still has others). Real semantics:
          - if user had only 1 address (the principal) and deletes it →
            count_active drops to 0 → next create auto-marks as principal. ✅
          - if user had 3 addresses and deletes the principal → count drops
            to 2, but neither of the remaining 2 has es_principal=True. The
            next create will see count=2 and NOT auto-mark.
        This matches D5 textually ("dejar sin predeterminada").
        """
        address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)
        if address is None:
            raise NotFoundError("Dirección no encontrada")
        self.uow.direcciones.delete(address_id)  # BaseRepository soft delete

    # ── Set principal (US-028, RN-DI02) ───────────────────────────────────

    def set_principal(
        self, user_id: int, address_id: int
    ) -> DireccionEntrega:
        """Atomic swap: unset previous principal, mark this one as principal.

        Both updates are staged in the SAME uow.session; the router's single
        uow.commit() commits them atomically. If the commit fails, the UoW
        rolls back both — the user is never left with 0 or 2 principals
        within the transaction boundary.

        Idempotent: if address is already principal, the unset+set sequence
        ends with the same state (no error, return the address).
        """
        address = self.uow.direcciones.find_by_id_and_user(address_id, user_id)
        if address is None:
            raise NotFoundError("Dirección no encontrada")

        # Step 1: unset whatever is currently principal for this user
        self.uow.direcciones.unset_principal_for_user(user_id)
        # Step 2: mark this one
        address.es_principal = True
        # NO flush() needed unless a subsequent read in the same request
        # depends on the new state. Router's uow.commit() will flush + commit.

        return address
```

Decisiones del service:
- **NUNCA hace `uow.commit()`** — deuda técnica D6 documentada en §10.
- En `update`, el `model_dump(exclude_unset=True)` permite distinguir "no enviado" de "null explícito". `referencia: null` queda `None` en DB (clear); `referencia: "  "` queda `None` (post-trim collapse).
- En `set_principal`, no se hace flush intermedio — SQLAlchemy autoflushes en el siguiente read si fuera necesario. El bulk UPDATE de `unset_principal_for_user` y la asignación `address.es_principal = True` se persisten juntos en el `commit()` del router.
- El service rechaza con `NotFoundError` ambos casos (no existe / no es propia). Esto es **D6** — patrón Rails anti-information-leak.

## 7. Router (`router.py`)

```python
"""
Delivery addresses API router — 5 endpoints for self-service address management.

All endpoints require authentication via Depends(get_current_user). Ownership
is enforced inside the service via find_by_id_and_user — a non-existent or
foreign address yields 404 (NOT 403) to prevent information leak (D6, RN-DI03).

Mounted at /api/v1/direcciones by backend/main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from backend.dependencies import get_uow
from backend.features.addresses.schemas import (
    DireccionCreate,
    DireccionRead,
    DireccionUpdate,
)
from backend.features.addresses.service import AddressService
from backend.features.auth.dependencies import get_current_user
from backend.features.users.models import Usuario
from backend.shared.unit_of_work import UnitOfWork

router = APIRouter()


@router.post("/", response_model=DireccionRead, status_code=status.HTTP_201_CREATED)
async def crear_direccion(
    payload: DireccionCreate,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Create a new delivery address.

    If the user has zero active addresses, the new one is auto-marked as
    principal (RN-DI01). Returns 201 with the created address.
    """
    service = AddressService(uow)
    address = service.create(current_user.id, payload)
    uow.commit()
    return DireccionRead.model_validate(address)


@router.get("/", response_model=list[DireccionRead])
async def listar_direcciones(
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> list[DireccionRead]:
    """List the authenticated user's active addresses (principal first)."""
    service = AddressService(uow)
    addresses = service.list_for_user(current_user.id)
    return [DireccionRead.model_validate(a) for a in addresses]


@router.put("/{address_id}", response_model=DireccionRead)
async def actualizar_direccion(
    address_id: int,
    payload: DireccionUpdate,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Partially update an address (PATCH semantics despite verb).

    Ownership: 404 if address doesn't exist OR belongs to another user (D6).
    """
    service = AddressService(uow)
    address = service.update(current_user.id, address_id, payload)
    uow.commit()
    return DireccionRead.model_validate(address)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_direccion(
    address_id: int,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> Response:
    """Soft-delete an address.

    Allowed even if it's the principal — per D5, the user is left with no
    principal. Returns 204 on success, 404 if not found or not owned.
    """
    service = AddressService(uow)
    service.delete(current_user.id, address_id)
    uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{address_id}/predeterminada", response_model=DireccionRead)
async def marcar_predeterminada(
    address_id: int,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Mark an address as the user's default (atomic swap).

    Unsets es_principal on whatever was principal previously and sets it on
    this one. Both updates committed in the same transaction (RN-DI02).
    """
    service = AddressService(uow)
    address = service.set_principal(current_user.id, address_id)
    uow.commit()
    return DireccionRead.model_validate(address)
```

Decisiones del router:
- Cada endpoint usa `Depends(get_current_user)` — cualquier rol autenticado. **NO se usa `require_role`** (no hay roles especiales para gestionar las propias direcciones).
- Las mutaciones (POST/PUT/DELETE/PATCH) hacen `uow.commit()` después del service. El GET no commitea (read-only).
- **Ningún endpoint acepta `user_id` en path o body** — el target user sale del JWT (RN-RB05, RN-DI03).
- El `PUT` tiene **semántica de PATCH** (partial update con `model_dump(exclude_unset=True)`). Es una decisión consciente para alinear con `docs/Historias_de_usuario.txt:1017` que pide `PUT /api/direcciones/:id`. El frontend puede mandar solo los campos que cambian.
- Ningún endpoint levanta `HTTPException` directamente — los errores tipados del service llegan a los handlers RFC 7807 globales (`backend/main.py:108-119`).

## 8. Manejo de errores (RFC 7807)

| Caso | Excepción | HTTP | Detail |
|------|-----------|------|--------|
| Sin token / token inválido | `UnauthorizedError` (lo levanta `get_current_user`) | 401 | "Token inválido o expirado" |
| Dirección no existe | `NotFoundError` | 404 | "Dirección no encontrada" |
| Dirección existe pero pertenece a OTRO usuario (D6) | `NotFoundError` | **404** | "Dirección no encontrada" *(NO 403, anti-leak)* |
| `calle`/`numero`/`ciudad`/`codigo_postal` vacío post-trim | `BusinessRuleError` | 422 | "El campo X no puede ser vacío" |
| Pydantic validation (min_length, max_length, tipo) | `RequestValidationError` | 422 | (auto, lista los fields) |
| Body con `es_principal` o `usuario_id` (anti-smuggling) | `RequestValidationError` | 422 | (auto, `extra="forbid"`) |
| Body con cualquier otro campo desconocido | `RequestValidationError` | 422 | (auto) |

Los handlers globales en `backend/main.py:108-119` ya producen RFC 7807 (`{type, title, status, detail, instance}`) — no se agregan handlers nuevos.

## 9. Riesgos de seguridad y decisiones explícitas

### Risk 1 — Atomicidad del swap PATCH /predeterminada

El swap requiere 2 UPDATEs lógicos:
1. `UPDATE delivery_addresses SET es_principal=false WHERE user_id=X AND es_principal=true AND eliminado_en IS NULL` (bulk).
2. `address.es_principal = true` (en-memoria, persistido en commit).

**Protección**: ambos staged en el mismo `uow.session`. El **router hace un solo `uow.commit()`** que los aplica atómicamente. Si el commit falla, la UoW rollbackea — el usuario nunca queda con 0 ni 2 principales DENTRO de la transacción. **No es necesario un `flush()` intermedio** porque la asignación `address.es_principal = True` no depende de la lectura del estado post-bulk.

### Risk 2 — Race condition: dos PATCH /predeterminada simultáneos

Escenario: el usuario abre dos pestañas y dispara `PATCH /A/predeterminada` y `PATCH /B/predeterminada` casi al mismo tiempo. Con READ COMMITTED (default Postgres) ambas transacciones pueden:
1. Leer el set de filas con `es_principal=true`.
2. Ejecutar el bulk UPDATE.
3. Marcar su address como principal.

El resultado puede ser: **2 direcciones con `es_principal=true`**.

**Aceptado** para un proyecto académico mono-usuario. Mitigaciones consideradas y descartadas:
- `SELECT ... FOR UPDATE` sobre las filas del usuario antes del bulk UPDATE — funciona pero requiere fetch adicional.
- Constraint partial unique `UNIQUE (user_id) WHERE es_principal AND eliminado_en IS NULL` — lo correcto pero requiere migración Alembic adicional.

Documentar como deuda técnica menor. En la práctica el único disparador real sería un usuario haciendo doble-click en la UI, y el efecto observable es solo "ambas aparecen marcadas hasta el próximo PATCH".

### Risk 3 — FK ON DELETE RESTRICT desde `orders.direccion_entrega_id`

La tabla `orders` (Sprint 5) tendrá FK a `delivery_addresses.id` con `ON DELETE RESTRICT` (verificado en explore). Como hacemos **soft delete** (no hard delete), el `eliminado_en IS NOT NULL` no afecta la FK física. Los pedidos históricos siguen apuntando válidamente a la dirección, y el snapshot `orders.direccion_snapshot` (ya definido en `backend/features/orders/models.py:48-52`) preserva el contenido textual aunque se modifique post-pedido.

Conclusión: **el soft delete es seguro**. La validación de "sin pedidos activos" mencionada en US-027 se difiere al Sprint 5 cuando exista la tabla `orders` con datos — agregarla ahora sería código muerto.

### Risk 4 — Anti-smuggling: campos prohibidos en POST/PUT

Sin `extra="forbid"`, un cliente malicioso podría enviar `{"calle": "...", "es_principal": true}` o `{"calle": "...", "usuario_id": 99}` y:
- Caso 1: marcar su nueva dirección como principal, contradiciendo D3 que dice "solo si es la primera".
- Caso 2: intentar crear una dirección a nombre de otro usuario (no funcionaría porque el service usa `current_user.id`, pero el body queda registrado en logs como sospechoso).

**Mitigación**: `model_config = {"extra": "forbid"}` en `DireccionCreate` y `DireccionUpdate`. Cualquier campo desconocido devuelve 422 con detail listando el field. Verificar en tests con `{"calle": ..., "es_principal": true}` → 422.

### Risk 5 — Ownership enforcement por 404, no 403 (D6)

**Decisión**: cuando una dirección no existe O pertenece a otro usuario, devolver `NotFoundError` → 404. NO 403.

Justificación (patrón Rails / GitHub):
- 403 "Forbidden" leakea la **existencia** del recurso ("este id existe pero no es tuyo"). Un atacante puede iterar IDs y mapear qué direcciones existen en el sistema.
- 404 "Not Found" no distingue entre "no existe" y "no es tuyo" — el atacante no puede distinguir.

**Implementación**: `find_by_id_and_user(id, user_id)` devuelve `None` en ambos casos. El service levanta `NotFoundError("Dirección no encontrada")` sin discriminar. El detail del response es genérico — no menciona "ajena" ni "permisos".

## 10. Decisión D6 (UoW) — el service no hace commit

Idéntica deuda técnica reconocida en `categories-backend`, `ingredients-backend`, `products-backend` y `user-profile-backend`.

**Patrón actual:**
- Router obtiene `uow: UnitOfWork = Depends(get_uow)`.
- Service recibe el `uow` y lo usa SOLO para registrar repos y operar.
- **Service NUNCA llama `uow.commit()`**.
- Router llama `uow.commit()` después del service en mutaciones; en reads no commitea.

**Por qué se mantiene:**
- Consistencia con los 4 changes previos del Sprint 4 / catálogo.
- Cambiar el patrón ahora implicaría refactor masivo fuera del scope de este change chico.
- Documentado como deuda — se resolverá globalmente en un change futuro de tipo "uow-context-manager-refactor" (no priorizado en `docs/CHANGES.md`).

## 11. Tests sugeridos (`backend/tests/integration/test_delivery_addresses.py`)

Patrón: clonar `test_user_profile.py` (para el patrón `Depends(get_current_user)` + ownership-via-JWT) y `test_ingredients.py` (para CRUD plano sin paginación). Reusar fixtures `client`, `sample_user`, `auth_headers` de `backend/tests/conftest.py`. Crear fixtures auxiliares localmente cuando sea necesario (p. ej. `second_user`, `second_user_auth_headers`).

### 11.1 Happy path (5 endpoints)

- `test_create_address_returns_201_with_full_payload` — POST con todos los campos válidos → 201, response tiene todos los campos incluido `id` y `es_principal`.
- `test_create_first_address_auto_marks_as_principal` — usuario sin direcciones, POST → response.es_principal == True (D3, RN-DI01).
- `test_create_second_address_does_not_auto_mark` — usuario con 1 principal existente, POST de otra → response.es_principal == False.
- `test_create_with_optional_fields_null` — POST sin `piso_depto` ni `referencia` → 201.
- `test_list_addresses_returns_only_own` — sembrar 2 direcciones para A y 1 para B; A llama GET → recibe solo sus 2.
- `test_list_addresses_principal_first` — sembrar 2 direcciones (id=1 no principal, id=2 principal); GET → orden `[id=2, id=1]`.
- `test_update_address_partial` — PUT con solo `{"calle": "Nueva Calle"}` → 200, `numero`/`ciudad`/etc preservados.
- `test_update_clear_optional_field_with_null` — PUT con `{"referencia": null}` → 200, columna queda `NULL`.
- `test_delete_address_soft_returns_204` — DELETE → 204, fila queda con `eliminado_en IS NOT NULL`, no aparece en GET /.
- `test_set_principal_returns_200_with_updated_address` — PATCH `/{id}/predeterminada` → 200, response.es_principal == True.

### 11.2 Ownership cross-user (CRÍTICO — D6)

- `test_get_other_user_address_returns_404` — A intenta GET por id de dirección de B → no existe ese path, pero PUT/DELETE/PATCH sí. Validar que PUT a id de B → 404 con detail genérico.
- `test_update_other_user_address_returns_404` — A hace PUT `/{id_de_B}` → 404 (no 403).
- `test_delete_other_user_address_returns_404` — A hace DELETE `/{id_de_B}` → 404.
- `test_set_principal_other_user_address_returns_404` — A hace PATCH `/{id_de_B}/predeterminada` → 404.
- `test_404_detail_does_not_leak_ownership` — verificar que el detail del 404 NO contiene las palabras "ajena", "propietario", "user", "permission".
- `test_list_excludes_other_users_addresses` — A llama GET / → las direcciones de B no aparecen.

### 11.3 Atomicidad de PATCH /predeterminada (CRÍTICO)

- `test_set_principal_unsets_previous_principal` — usuario tiene addrA(principal) y addrB; PATCH `/addrB/predeterminada` → en DB addrA.es_principal == False AND addrB.es_principal == True.
- `test_set_principal_idempotent` — usuario tiene addrA(principal); PATCH `/addrA/predeterminada` → 200, addrA.es_principal sigue True (sin error).
- `test_set_principal_when_user_has_no_principal` — usuario tiene addrA y addrB ambas no-principal (escenario post-borrado de la principal); PATCH `/addrA/predeterminada` → addrA queda principal, addrB sigue no-principal.

### 11.4 Borrar la principal (D5)

- `test_delete_principal_leaves_user_without_principal` — usuario tiene addrA(principal) y addrB(no); DELETE addrA → en DB addrA.eliminado_en IS NOT NULL, addrB.es_principal sigue False.
- `test_after_delete_principal_next_create_is_auto_principal` — usuario tiene addrA(principal); DELETE addrA → POST nueva addrC → addrC.es_principal == True (porque ahora hay 0 activas).

### 11.5 Anti-smuggling (CRÍTICO — Risk #4)

- `test_create_with_es_principal_in_body_returns_422` — POST con `{"calle": "...", ..., "es_principal": true}` → 422 (`extra="forbid"`).
- `test_create_with_usuario_id_in_body_returns_422` — POST con `{"calle": "...", ..., "usuario_id": 999}` → 422.
- `test_update_with_es_principal_in_body_returns_422` — PUT con `{"es_principal": true}` → 422 (la única manera legítima es PATCH /predeterminada).
- `test_update_with_unknown_field_returns_422` — PUT con `{"foo": "bar"}` → 422.

### 11.6 Validación Pydantic / business rules

- `test_create_with_empty_calle_returns_422` — POST con `{"calle": ""}` → 422 (Pydantic min_length=1).
- `test_create_with_whitespace_only_calle_returns_422` — POST con `{"calle": "   "}` → 422 (BusinessRuleError post-trim).
- `test_create_with_calle_too_long_returns_422` — 256 chars → 422.
- `test_create_missing_required_field_returns_422` — POST sin `numero` → 422.

### 11.7 Auth / RBAC

- `test_endpoints_without_token_return_401` — GET/POST/PUT/DELETE/PATCH sin Authorization header → 401.
- `test_endpoints_with_invalid_token_return_401` — `Bearer foobar` → 401.
- `test_admin_user_uses_endpoints_too` — usuario con rol ADMIN puede usar todos los endpoints sobre sus propias direcciones (cualquier rol autenticado).

## 12. Pre-flight check del propose

- ✅ Roadmap: `delivery-addresses-backend` aparece en `docs/CHANGES.md:118-123` como change #13 del Sprint 4.
- ✅ Dependencias: `auth-backend`, `auth-backend-stabilization`, `database-migrations`, `base-entities`, `categories-backend`, `ingredients-backend`, `products-backend`, `user-profile-backend` archivados en `openspec/changes/archive/`.
- ✅ Decisiones cerradas: D1, D3, D5, D6, D9 explícitas en el prompt del usuario y registradas en proposal §"Decisiones cerradas" + design §9.
- ✅ Patrón a clonar: `users/` (especialmente `Depends(get_current_user)` + ownership-via-JWT) + `ingredients/` (CRUD plano sin paginación).
- ✅ No hay assumptions nuevos pendientes de cierre — los risks están todos documentados y aceptados (#2 race condition mono-usuario, #3 FK postergada al Sprint 5).
