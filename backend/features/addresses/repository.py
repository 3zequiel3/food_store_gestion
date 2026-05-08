"""
Address repository — data access for DireccionEntrega.

Inherits CRUD (create/read/update/soft-delete/list) from BaseRepository.
Adds methods specialised for ownership enforcement (D6) and principal-address
bookkeeping (RN-DI01, RN-DI02, RN-DI03).

Import chain (regla de oro): repository → models, shared.repository.
No imports from service, router, or FastAPI.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select, update
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
        """Return the address only if it belongs to user_id AND is active.

        Single source of truth for ownership enforcement (D6):
        returns None both when the address doesn't exist AND when it belongs
        to another user. The service interprets None as NotFoundError → 404
        (intentional anti-leak — see Risk #5 in design.md).
        """
        query = (
            self._get_base_query()
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

        Helper for tests / defensive checks. NOT used in the swap path —
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

        Does NOT call session.flush() — leaves ordering to the caller.
        """
        stmt = (
            update(DireccionEntrega)
            .where(DireccionEntrega.user_id == user_id)
            .where(DireccionEntrega.eliminado_en.is_(None))
            .where(DireccionEntrega.es_principal.is_(True))
            .values(es_principal=False)
        )
        self.session.execute(stmt)
