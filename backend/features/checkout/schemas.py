"""Schemas for checkout module."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CheckoutItem(BaseModel):
    """Item in checkout request."""
    
    model_config = ConfigDict(extra="forbid")
    
    producto_id: int = Field(..., ge=1, description="Product ID (must be >= 1)")
    cantidad: int = Field(..., ge=1, description="Quantity (must be >= 1)")
    personalizacion: list[int] | None = Field(
        default=None,
        description="Optional list of ingredient IDs to customize"
    )
    
    @field_validator('personalizacion')
    @classmethod
    def validate_personalizacion(cls, v: list[int] | None) -> list[int] | None:
        """Ensure all personalization IDs are >= 1."""
        if v is not None:
            for pid in v:
                if pid is not None and pid >= 1:
                    continue
                raise ValueError(f"Personalization IDs must be >= 1, got {pid}")
        return v


class CheckoutOnlineRequest(BaseModel):
    """Request to create an order with online payment."""
    
    model_config = ConfigDict(extra="forbid")
    
    items: list[CheckoutItem] = Field(..., min_length=1)
    tipo_entrega: Literal["DELIVERY", "PICKUP"] = Field(...)
    direccion_id: int | None = Field(default=None)
    notas: str | None = Field(default=None, max_length=500)
    
    # Payment fields
    card_token: str = Field(..., min_length=1)
    payment_method_id: str = Field(..., min_length=1)
    installments: int = Field(default=1, ge=1)
    idempotency_key: UUID = Field(...)
    identification_type: str = Field(..., min_length=1)
    identification_number: str = Field(..., min_length=1)
    payer_email: str = Field(..., min_length=1)


class CheckoutPickupEfectivoRequest(BaseModel):
    """Request to create a pickup order with cash payment."""

    model_config = ConfigDict(extra="forbid")

    items: list[CheckoutItem] = Field(..., min_length=1)
    notas: str | None = Field(default=None, max_length=500)
    # Note: no direccion_id, no payment fields


class CheckoutDeliveryEfectivoRequest(BaseModel):
    """
    Request to create a delivery order with cash payment (P0.2).

    The customer pays in cash at the door when the order is delivered.
    The order is created in PENDIENTE state with shipping cost applied.
    No Pago record is created — payment is tracked manually at delivery time.
    """

    model_config = ConfigDict(extra="forbid")

    items: list[CheckoutItem] = Field(..., min_length=1)
    direccion_id: int = Field(..., ge=1, description="Delivery address ID (required for cash-on-delivery)")
    notas: str | None = Field(default=None, max_length=500)


class CheckoutDeliveryEfectivoResponse(BaseModel):
    """Response for successful cash-on-delivery checkout."""

    pedido_id: int


class CheckoutOnlineResponse(BaseModel):
    """Response for successful online checkout."""
    
    pedido_id: int
    pago_id: int
    mp_status: str
    mp_id: str
    status_detail: str


class CheckoutPickupEfectivoResponse(BaseModel):
    """Response for successful pickup+cash checkout."""
    
    pedido_id: int


class CheckoutErrorResponse(BaseModel):
    """Error response for checkout failures."""
    
    code: str
    detail: str
    mp_status: str | None = Field(default=None)
    status_detail: str | None = Field(default=None)
