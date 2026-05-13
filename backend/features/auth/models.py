"""
Auth domain model: RefreshToken.

Stores persisted refresh tokens so they can be revoked (RN-AU03, RN-AU04).
Each token is stored as a SHA-256 hash — never the raw token string.

Replay attack detection (RN-AU05) is modeled via ``revoked_at``:
- A successful refresh sets ``revoked_at`` on the old token and issues a new one.
- If a token with ``revoked_at IS NOT NULL`` is presented again, it is treated
  as a compromise and ALL tokens of that user are revoked immediately.
- There is no ``family_id`` (not in ERD v5 §3.1) and no ``used`` flag;
  ``revoked_at IS NOT NULL`` covers both rotation and replay semantics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel


class RefreshToken(BaseModel):
    """
    Persisted refresh token for JWT-based auth.

    - ``token_hash``: SHA-256 hex digest of the raw refresh token (CHAR 64, never stored plain).
    - ``expires_at``: when the token ceases to be valid (7 days from creation).
    - ``revoked_at``: nullable; set when the token is explicitly revoked (logout / rotation / replay).

    RN-AU05: If a token with revoked_at set is presented again, ALL tokens of the
    user are revoked (``UPDATE refresh_tokens SET revoked_at=now() WHERE user_id=?``).
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship back to user
    usuario: Mapped["backend.features.users.models.Usuario"] = relationship(
        "Usuario",
        back_populates="refresh_tokens",
        lazy="select",
    )

    @property
    def is_active(self) -> bool:
        """Check if token is still valid (not revoked, not expired)."""
        now = datetime.now(timezone.utc)
        return (
            self.revoked_at is None
            and self.expires_at > now
        )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked_at is not None})>"
