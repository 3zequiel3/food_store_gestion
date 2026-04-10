"""
Order domain model.
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship

from backend.shared.models import BaseModel
from backend.shared.enums import EstadoPedido


class Order(BaseModel):
    """
    Order entity.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        total: Order total amount (decimal)
        estado: Order status (EstadoPedido enum)
        delivery_address: Address for delivery
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "orders"

    user_id = Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total = Column(Numeric(10, 2), nullable=False)
    estado = Column(
        Enum(EstadoPedido),
        default=EstadoPedido.PENDIENTE,
        nullable=False,
        index=True,
    )
    delivery_address = Column(String(500), nullable=True)
    deleted_at = Column(
        DateTime, nullable=True, index=True, comment="Soft delete timestamp"
    )

    # Relationships
    user = relationship("User", back_populates="orders")
    payment = relationship(
        "Payment", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    order_items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        foreign_keys="OrderItem.order_id",
    )

    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, total={self.total})>"


class OrderItem(BaseModel):
    """
    Order item (line item in an order).

    Stub for future implementation - referenced in Order relationship.
    """

    __tablename__ = "order_items"

    order_id = Column(
        "order_id",
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        "product_id",
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity = Column(Numeric(5, 0), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="order_items", foreign_keys=[order_id])

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id})>"
