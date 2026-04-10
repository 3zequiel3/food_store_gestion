"""
Base SQLAlchemy models with common fields.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, UUID, func
from sqlalchemy.orm import declarative_base, DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class BaseModel(Base):
    """
    Base model for all entities.

    Provides common fields:
    - id: UUID primary key
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
