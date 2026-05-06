"""
Auth domain model: RefreshToken.

Stores persisted refresh tokens so they can be revoked (RN-AU03, RN-AU04).
Each token is stored as a SHA-256 hash — never the raw token string.
Includes family_id for replay attack detection (RN-AU05).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel


class RefreshToken(BaseModel):
    """
    Persisted refresh token for JWT-based auth.

    - ``token_hash``: SHA-256 hash of the raw refresh token (never stored plain).
    - ``family_id``: UUID v4 that groups tokens in a "family" for replay attack detection.
    - ``used``: Flag indicating if the token has been consumed (rotation).
    - ``expires_at``: when the token ceases to be valid.
    - ``revoked_at``: nullable; set when the token is explicitly revoked (logout / replay attack).

    RN-AU05: If a used token is presented again, ALL tokens in the family are revoked.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
        """Check if token is still valid (not used, not revoked, not expired)."""
        now = datetime.utcnow()
        return (
            not self.used
            and self.revoked_at is None
            and self.expires_at > now
        )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, used={self.used})>"
