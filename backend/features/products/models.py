"""
Product domain model.
"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Numeric, String, func

from backend.shared.models import BaseModel


class Product(BaseModel):
    """
    Product entity.

    Attributes:
        id: UUID primary key
        name: Product name
        description: Product description
        price: Product price (decimal)
        is_active: Whether product is active
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "products"

    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    deleted_at = Column(
        DateTime, nullable=True, index=True, comment="Soft delete timestamp"
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"
