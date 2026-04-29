"""
Auth domain model: RefreshToken.

Stores persisted refresh tokens so they can be revoked (RN-DA09).
Each token is stored as a bcrypt/SHA hash — never the raw token string.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel


class RefreshToken(BaseModel):
    """
    Persisted refresh token for JWT-based auth.

    - ``token_hash``: SHA-256 hash of the raw refresh token (never stored plain).
    - ``expires_at``: when the token ceases to be valid.
    - ``revoked_at``: nullable; set when the token is explicitly revoked (logout / rotation).
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

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
