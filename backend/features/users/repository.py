"""
UserProfile repository.

Provides data access for user profile self-service operations.
Only adds find_by_id_with_roles; all standard CRUD is inherited from BaseRepository.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.features.users.models import Usuario
from backend.shared.repository import BaseRepository


class UserProfileRepository(BaseRepository[Usuario]):
    """Repository for user profile operations (self-service only).

    Inherits create/read/update/delete/list from BaseRepository[Usuario].
    Adds find_by_id_with_roles for eager-loading the M2N roles relationship.
    """

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def find_by_id_with_roles(self, user_id: int) -> Optional[Usuario]:
        """Read a Usuario eager-loading its roles[] relationship.

        Used by GET /me and PATCH /me to serialize ProfileResponse without
        triggering a lazy-load on `roles` after the session closes.

        Excludes soft-deleted users (eliminado_en IS NOT NULL) — inherited from
        _get_base_query().  If get_current_user already returned the user, they
        are guaranteed active; this filter is a defensive extra check.

        Uses selectinload (not joinedload) to avoid cartesian products when a
        user has multiple roles.
        """
        query = (
            self._get_base_query()
            .where(Usuario.id == user_id)
            .options(selectinload(Usuario.roles))
        )
        return self.session.execute(query).scalar_one_or_none()
