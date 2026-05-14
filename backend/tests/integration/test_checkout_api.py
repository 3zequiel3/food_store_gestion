"""
Integration tests for delivery+payment validation and Checkout API
(payment-checkout-api-implementation).

Runner: cd backend && uv run pytest tests/integration/test_checkout_api.py -v
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PAGOS_URL = "/api/v1/pagos"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pedido(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in PENDIENTE state belonging to sample_user."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("150.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


def _mock_sdk(payment_status="approved", payment_id="mp_pay_001"):
    """Build a MagicMock that mimics the MercadoPago SDK for Checkout API."""
    sdk = MagicMock()
    sdk.payment.return_value.create.return_value = {
        "response": {
            "status": payment_status,
            "id": payment_id,
            "status_detail": "accredited",
        }
    }
    return sdk


# ---------------------------------------------------------------------------
# POST /api/v1/pagos — Checkout API
# ---------------------------------------------------------------------------


class TestCheckoutApi:
    def test_pago_valido_retorna_201(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """Happy path: valid PENDIENTE order → 201 + mp_status=approved."""
        mock_sdk = _mock_sdk(payment_status="approved")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        body = response.json()
        assert body["mp_status"] == "approved"
        assert body["mp_id"] == "mp_pay_001"
        assert body["status_detail"] == "accredited"

    def test_pedido_de_otro_usuario_retorna_403(
        self, client: TestClient, test_db_session: Session, sample_roles, sample_pedido
    ):
        """Order owned by a different user → 403."""
        from features.users.models import Usuario, UsuarioRol
        from shared.security import hash_password

        user = Usuario(
            email="otro_checkout@example.com",
            password_hash=hash_password("otro_pw_123"),
            nombre="Otro",
            apellido="Usuario",
            is_active=True,
        )
        test_db_session.add(user)
        test_db_session.flush()
        test_db_session.add(UsuarioRol(user_id=user.id, role_id=4))  # CLIENT
        test_db_session.commit()

        client.post(
            "/api/v1/auth/login",
            json={"email": "otro_checkout@example.com", "password": "otro_pw_123"},
        )

        mock_sdk = _mock_sdk()
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440001",
                },
            )

        assert response.status_code == 403

    def test_pedido_no_pendiente_retorna_409(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_user,
        sample_formas_pago,
        sample_estados_pedido,
    ):
        """Order not in PENDIENTE state → 409."""
        from features.orders.models import Pedido

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("100.00"),
            costo_envio=Decimal("50.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        mock_sdk = _mock_sdk()
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440002",
                },
                headers=auth_headers,
            )

        assert response.status_code == 409

    def test_pago_activo_previo_retorna_409(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """Existing active payment blocks new attempt → 409."""
        from features.payments.models import Pago
        import uuid

        pago_rechazado = Pago(
            pedido_id=sample_pedido.id,
            monto=Decimal("150.00"),
            forma_pago_codigo="MERCADOPAGO",
            idempotency_key=str(uuid.uuid4()),
            mp_status="pending",
        )
        test_db_session.add(pago_rechazado)
        test_db_session.commit()

        mock_sdk = _mock_sdk()
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440003",
                },
                headers=auth_headers,
            )

        assert response.status_code == 409

    def test_pago_rechazado_retorna_error(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """MP rejects payment → error response, no state change."""
        mock_sdk = _mock_sdk(payment_status="rejected", payment_id="mp_rej_001")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440004",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422  # BusinessRuleError → 422

    def test_idempotency_key_invalid_uuid_422(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """Invalid UUID format for idempotency_key → 422 (Pydantic validation)."""
        response = client.post(
            PAGOS_URL + "/",
            json={
                "pedido_id": sample_pedido.id,
                "card_token": "tok_test_123",
                "payment_method_id": "visa",
                "installments": 1,
                "idempotency_key": "not-a-uuid",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_approved_transitions_order_to_confirmado(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """Approved payment → order moves to CONFIRMADO."""
        mock_sdk = _mock_sdk(payment_status="approved")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                PAGOS_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440005",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201

        test_db_session.expire_all()

        from features.orders.models import Pedido
        from sqlalchemy import select as sa_select

        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "CONFIRMADO"


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
