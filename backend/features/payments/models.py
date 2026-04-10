"""
Payment domain model.
"""

from sqlalchemy import Column, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from backend.shared.models import BaseModel
from backend.shared.enums import FormaPago


class Payment(BaseModel):
    """
    Payment entity.

    Attributes:
        id: UUID primary key
        order_id: Foreign key to Order
        amount: Payment amount (decimal)
        method: Payment method (FormaPago enum)
        status: Payment status (pending, completed, failed)
        external_id: External payment ID (MercadoPago, etc.)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "payments"

    order_id = Column(
        "order_id",
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One payment per order
    )
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum(FormaPago), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)

    # Relationships
    order = relationship("Order", back_populates="payment")

    def __repr__(self):
        return (
            f"<Payment(id={self.id}, order_id={self.order_id}, amount={self.amount})>"
        )
