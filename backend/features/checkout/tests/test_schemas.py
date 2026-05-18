"""Tests for checkout schemas (TDD - RED phase)."""

import uuid

import pytest
from pydantic import ValidationError

from features.checkout.schemas import (
    CheckoutErrorResponse,
    CheckoutItem,
    CheckoutOnlineRequest,
    CheckoutOnlineResponse,
    CheckoutPickupEfectivoRequest,
    CheckoutPickupEfectivoResponse,
)


class TestCheckoutItem:
    """Tests for CheckoutItem schema."""
    
    def test_valid_item(self):
        """Should accept valid item with all fields."""
        item = CheckoutItem(
            producto_id=1,
            cantidad=2,
            personalizacion=[1, 2, 3]
        )
        assert item.producto_id == 1
        assert item.cantidad == 2
        assert item.personalizacion == [1, 2, 3]
    
    def test_valid_item_without_personalizacion(self):
        """Should accept item without personalization."""
        item = CheckoutItem(
            producto_id=1,
            cantidad=2,
            personalizacion=None
        )
        assert item.personalizacion is None
    
    def test_producto_id_must_be_positive(self):
        """Should reject producto_id = 0."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=0, cantidad=1)
        assert "producto_id" in str(exc_info.value)
    
    def test_producto_id_must_be_at_least_one(self):
        """Should reject producto_id = -1."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=-1, cantidad=1)
        assert "producto_id" in str(exc_info.value)
    
    def test_cantidad_must_be_positive(self):
        """Should reject cantidad = 0."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=1, cantidad=0)
        assert "cantidad" in str(exc_info.value)
    
    def test_cantidad_must_be_at_least_one(self):
        """Should reject cantidad = -5."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=1, cantidad=-5)
        assert "cantidad" in str(exc_info.value)
    
    def test_personalizacion_with_zero_rejected(self):
        """Should reject personalizacion containing 0."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=1, cantidad=1, personalizacion=[0, 1, 2])
        assert "personalizacion" in str(exc_info.value)
    
    def test_personalizacion_with_negative_rejected(self):
        """Should reject personalizacion containing negative."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutItem(producto_id=1, cantidad=1, personalizacion=[-1, 1, 2])
        assert "personalizacion" in str(exc_info.value)
    
    def test_personalizacion_with_valid_ids_accepted(self):
        """Should accept personalizacion with valid IDs >= 1."""
        item = CheckoutItem(
            producto_id=1,
            cantidad=1,
            personalizacion=[1, 2, 3, 100]
        )
        assert item.personalizacion == [1, 2, 3, 100]


class TestCheckoutOnlineRequest:
    """Tests for CheckoutOnlineRequest schema."""
    
    def test_valid_request(self):
        """Should accept valid online checkout request."""
        request = CheckoutOnlineRequest(
            items=[
                CheckoutItem(producto_id=1, cantidad=2),
                CheckoutItem(producto_id=2, cantidad=1)
            ],
            tipo_entrega="DELIVERY",
            direccion_id=42,
            notas="Sin cebolla",
            card_token="token123",
            payment_method_id="master",
            installments=1,
            idempotency_key=uuid.uuid4(),
            identification_type="DNI",
            identification_number="12345678"
        )
        assert request.tipo_entrega == "DELIVERY"
        assert request.direccion_id == 42
        assert len(request.items) == 2
    
    def test_valid_request_with_pickup(self):
        """Should accept valid request with PICKUP type."""
        request = CheckoutOnlineRequest(
            items=[CheckoutItem(producto_id=1, cantidad=1)],
            tipo_entrega="PICKUP",
            direccion_id=None,
            card_token="token123",
            payment_method_id="visa",
            installments=3,
            idempotency_key=uuid.uuid4(),
            identification_type="DNI",
            identification_number="12345678"
        )
        assert request.tipo_entrega == "PICKUP"
        assert request.direccion_id is None
    
    def test_direccion_id_nullable(self):
        """Should accept null direccion_id."""
        request = CheckoutOnlineRequest(
            items=[CheckoutItem(producto_id=1, cantidad=1)],
            tipo_entrega="PICKUP",
            direccion_id=None,
            card_token="token123",
            payment_method_id="visa",
            idempotency_key=uuid.uuid4(),
            identification_type="DNI",
            identification_number="12345678"
        )
        assert request.direccion_id is None
    
    def test_invalid_tipo_entrega_rejected(self):
        """Should reject tipo_entrega not in enum."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutOnlineRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                tipo_entrega="INVALID",
                card_token="token123",
                payment_method_id="visa",
                idempotency_key=uuid.uuid4(),
                identification_type="DNI",
                identification_number="12345678"
            )
        assert "tipo_entrega" in str(exc_info.value)
    
    def test_invalid_uuid_rejected(self):
        """Should reject invalid idempotency_key."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutOnlineRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                tipo_entrega="DELIVERY",
                card_token="token123",
                payment_method_id="visa",
                idempotency_key="not-a-uuid",  # type: ignore
                identification_type="DNI",
                identification_number="12345678"
            )
        assert "idempotency_key" in str(exc_info.value)
    
    def test_extra_field_rejected(self):
        """Should reject extra fields (extra=forbid)."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutOnlineRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                tipo_entrega="DELIVERY",
                card_token="token123",
                payment_method_id="visa",
                idempotency_key=uuid.uuid4(),
                identification_type="DNI",
                identification_number="12345678",
                extra_field="should fail"  # type: ignore
            )
        assert "extra_field" in str(exc_info.value)
    
    def test_empty_items_rejected(self):
        """Should reject empty items list."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutOnlineRequest(
                items=[],  # type: ignore
                tipo_entrega="DELIVERY",
                card_token="token123",
                payment_method_id="visa",
                idempotency_key=uuid.uuid4(),
                identification_type="DNI",
                identification_number="12345678"
            )
        assert "items" in str(exc_info.value)
    
    def test_missing_required_field_rejected(self):
        """Should reject missing card_token."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutOnlineRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                tipo_entrega="DELIVERY",
                card_token="",  # Empty string fails min_length
                payment_method_id="visa",
                idempotency_key=uuid.uuid4(),
                identification_type="DNI",
                identification_number="12345678"
            )
        assert "card_token" in str(exc_info.value)


class TestCheckoutPickupEfectivoRequest:
    """Tests for CheckoutPickupEfectivoRequest schema."""
    
    def test_valid_request(self):
        """Should accept valid pickup+efectivo request."""
        request = CheckoutPickupEfectivoRequest(
            items=[CheckoutItem(producto_id=1, cantidad=2)],
            notas="Llamar antes de entregar"
        )
        assert len(request.items) == 1
        assert request.notas == "Llamar antes de entregar"
    
    def test_direccion_id_not_accepted(self):
        """Should reject direccion_id field."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutPickupEfectivoRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                direccion_id=42  # type: ignore
            )
        assert "direccion_id" in str(exc_info.value)
    
    def test_card_token_not_accepted(self):
        """Should reject card_token field."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutPickupEfectivoRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                card_token="token123"  # type: ignore
            )
        assert "card_token" in str(exc_info.value)
    
    def test_extra_forbid(self):
        """Should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            CheckoutPickupEfectivoRequest(
                items=[CheckoutItem(producto_id=1, cantidad=1)],
                extra_field="should fail"  # type: ignore
            )
        assert "extra_field" in str(exc_info.value)


class TestCheckoutOnlineResponse:
    """Tests for CheckoutOnlineResponse schema."""
    
    def test_valid_response(self):
        """Should accept valid online checkout response."""
        response = CheckoutOnlineResponse(
            pedido_id=123,
            pago_id=456,
            mp_status="approved",
            mp_id="payment_789",
            status_detail="accredited"
        )
        assert response.pedido_id == 123
        assert response.pago_id == 456
        assert response.mp_status == "approved"


class TestCheckoutPickupEfectivoResponse:
    """Tests for CheckoutPickupEfectivoResponse schema."""
    
    def test_valid_response(self):
        """Should accept valid pickup+efectivo response."""
        response = CheckoutPickupEfectivoResponse(
            pedido_id=123
        )
        assert response.pedido_id == 123


class TestCheckoutErrorResponse:
    """Tests for CheckoutErrorResponse schema."""
    
    def test_valid_error_with_mp_fields(self):
        """Should accept error response with MP fields."""
        error = CheckoutErrorResponse(
            code="payment_rejected",
            detail="Saldo insuficiente",
            mp_status="rejected",
            status_detail="cc_rejected_insufficient_amount"
        )
        assert error.code == "payment_rejected"
        assert error.mp_status == "rejected"
        assert error.status_detail == "cc_rejected_insufficient_amount"
    
    def test_valid_error_without_mp_fields(self):
        """Should accept error response without MP fields."""
        error = CheckoutErrorResponse(
            code="validation_error",
            detail="Datos inválidos"
        )
        assert error.code == "validation_error"
        assert error.mp_status is None
        assert error.status_detail is None
