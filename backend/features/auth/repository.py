"""
RefreshToken repository.

Provides data access methods for refresh token management including
token lookup, revocation, and replay attack detection.
"""

from datetime import datetime, timezone
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

        Sets revoked_at on every non-revoked token of the user.

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
            .values(revoked_at=datetime.now(timezone.utc))
        )
        return result.rowcount

    def mark_token_as_revoked(self, token_id: int) -> None:
        """
        Mark a specific token as revoked (consumed during rotation or logout).

        Sets revoked_at to the current UTC timestamp.

        Args:
            token_id: The token's primary key
        """
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
