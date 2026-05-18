"""
Integration tests for delivery+payment validation.
(payment-checkout-api-implementation)

NOTE: The TestCheckoutApi class tested POST /api/v1/pagos/ which was eliminated
in the checkout-pay-first-flow change. Those behaviors are now covered by the
CheckoutService unit tests (features/checkout/tests/test_service_online.py)
and the checkout router integration tests.

Runner: cd backend && uv run pytest tests/integration/test_checkout_api.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Delivery + payment validation
# ---------------------------------------------------------------------------


class TestDeliveryPaymentValidation:
    @pytest.mark.pg_only
    def test_efectivo_con_direccion_rechazado(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_formas_pago,
        sample_producto_disponible,
        sample_address,
    ):
        """EFECTIVO + direccion_id → 422 (invalid payment for delivery)."""
        response = client.post(
            "/api/v1/pedidos/",
            json={
                "items": [
                    {"producto_id": sample_producto_disponible.id, "cantidad": 1}
                ],
                "forma_pago_codigo": "EFECTIVO",
                "direccion_id": sample_address.id,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "efectivo" in response.json()["detail"].lower()

    @pytest.mark.pg_only
    def test_efectivo_sin_direccion_ok(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """EFECTIVO without direccion_id (retiro en local) → 201."""
        response = client.post(
            "/api/v1/pedidos/",
            json={
                "items": [
                    {"producto_id": sample_producto_disponible.id, "cantidad": 1}
                ],
                "forma_pago_codigo": "EFECTIVO",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    @pytest.mark.pg_only
    def test_tarjeta_con_direccion_ok(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_formas_pago,
        sample_producto_disponible,
        sample_address,
    ):
        """TARJETA (MERCADOPAGO) + direccion_id → 201."""
        response = client.post(
            "/api/v1/pedidos/",
            json={
                "items": [
                    {"producto_id": sample_producto_disponible.id, "cantidad": 1}
                ],
                "forma_pago_codigo": "MERCADOPAGO",
                "direccion_id": sample_address.id,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
