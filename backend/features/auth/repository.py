"""
RefreshToken repository.

Provides data access methods for refresh token management including
token lookup, revocation, and replay attack detection.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.features.auth.models import RefreshToken
from backend.shared.repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for RefreshToken entity."""

    def __init__(self, session: Session):
        super().__init__(session, RefreshToken)

    def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Find a refresh token by its hash.

        Args:
            token_hash: SHA-256 hash of the token

        Returns:
            RefreshToken instance or None
        """
        query = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        return self.session.execute(query).scalar_one_or_none()

    def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke ALL refresh tokens for a user (RN-AU05 replay attack protection).

        Args:
            user_id: The user's ID

        Returns:
            Number of tokens revoked
        """
        result = self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        return result.rowcount

    def revoke_family_tokens(self, family_id: uuid.UUID) -> int:
        """
        Revoke ALL tokens in a family (RN-AU05 replay attack protection).

        Args:
            family_id: The token family UUID

        Returns:
            Number of tokens revoked
        """
        result = self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        return result.rowcount

    def mark_token_as_used(self, token_id: int) -> None:
        """
        Mark a token as used (consumed during rotation).

        Args:
            token_id: The token's ID
        """
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(used=True)
        )
