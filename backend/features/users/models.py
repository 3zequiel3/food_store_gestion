"""
User domain model.
"""

from sqlalchemy import Boolean, Column, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from backend.shared.models import BaseModel
from backend.shared.enums import Role


class User(BaseModel):
    """
    User entity.

    Attributes:
        id: UUID primary key
        email: Unique email address
        username: Unique username
        password_hash: Hashed password (added in auth feature)
        is_active: Whether user is active
        role_id: User role (ADMIN, USER, DELIVERY)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(Enum(Role), default=Role.USER, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
