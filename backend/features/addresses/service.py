"""
Address service — self-service address management for authenticated users.

Registered repository: uow.direcciones → AddressRepository.

CRITICAL: This service NEVER calls uow.commit() — the router decides the
transaction boundary (D6, per consistent pattern with all other features).

Import chain (regla de oro): service → repository → models, shared.
No imports from FastAPI, router, or schemas as type hints (service returns ORM objects).
"""
from __future__ import annotations

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
        will auto-mark by D3 only if count of active addresses drops to 0.
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
