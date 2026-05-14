"""
Integration tests for payments endpoints (Sprint 5 #15).

Endpoints under test:
  POST /api/v1/pagos                      — create MP preference
  POST /api/v1/pagos/webhook/mercadopago  — IPN handler
  GET  /api/v1/pagos/pedido/{pedido_id}   — latest payment status

MercadoPago SDK is always mocked — tests never hit external APIs.

All tests run on SQLite (payments and orders tables have no ARRAY(Integer) columns).

Webhook format tolerance — three MP notification formats are tested:
  Format 1 — Modern webhook: POST JSON {"type": "payment", "data": {"id": "123"}}
  Format 2 — Old IPN body:   POST JSON {"topic": "payment", "resource": "https://.../payments/123"}
  Format 3 — Classic IPN:    GET/POST ?topic=payment&id=123 (empty body)
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BASE_URL = "/api/v1/pagos"
WEBHOOK_URL = "/api/v1/pagos/webhook/mercadopago"


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


@pytest.fixture
def otro_usuario(test_db_session: Session, sample_roles):
    """A second client user — used to test ownership enforcement."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="otro@example.com",
        password_hash=hash_password("otro_password_123"),
        nombre="Otro",
        apellido="Usuario",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=4))  # CLIENT
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def otro_auth_headers(client, otro_usuario):
    """Auth headers for otro_usuario."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "otro@example.com", "password": "otro_password_123"},
    )
    return {}


@pytest.fixture
def sample_pago(test_db_session: Session, sample_pedido):
    """A Pago in 'pending' state linked to sample_pedido."""
    from features.payments.models import Pago
    import uuid

    pago = Pago(
        pedido_id=sample_pedido.id,
        monto=Decimal("150.00"),
        forma_pago_codigo="MERCADOPAGO",
        idempotency_key=str(uuid.uuid4()),
        mp_status="pending",
    )
    test_db_session.add(pago)
    test_db_session.commit()
    test_db_session.refresh(pago)
    return pago


def _mock_sdk(
    init_point="https://mp.com/init",
    payment_status="approved",
    external_reference=None,
    payment_id="mp_pay_001",
):
    """Build a MagicMock that mimics the MercadoPago SDK."""
    sdk = MagicMock()
    sdk.preference.return_value.create.return_value = {
        "response": {"init_point": init_point, "id": "pref_123"}
    }
    sdk.payment.return_value.create.return_value = {
        "response": {
            "status": payment_status,
            "id": payment_id,
            "status_detail": "accredited",
            "external_reference": external_reference or "",
        }
    }
    sdk.payment.return_value.get.return_value = {
        "response": {
            "status": payment_status,
            "external_reference": external_reference or "",
        }
    }
    return sdk


# ---------------------------------------------------------------------------
# POST /api/v1/pagos — Checkout API (direct card charge)
# ---------------------------------------------------------------------------


class TestCrearPago:
    def test_7_2_pago_valido_retorna_201_con_mp_status(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """Happy path: valid PENDIENTE order → 201 + mp_status=approved."""
        mock_sdk = _mock_sdk(payment_status="approved", payment_id="mp_pay_001")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
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

    def test_7_3_pedido_de_otro_usuario_retorna_403(
        self, client: TestClient, otro_auth_headers: dict, sample_pedido
    ):
        """Order owned by a different user → 403."""
        mock_sdk = _mock_sdk()
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440001",
                },
                headers=otro_auth_headers,
            )

        assert response.status_code == 403

    def test_7_4_pedido_confirmado_retorna_409(
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
                BASE_URL + "/",
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

    def test_7_5_pago_activo_previo_retorna_409(
        self, client: TestClient, auth_headers: dict, sample_pedido, sample_pago
    ):
        """Existing active payment (mp_status=pending) blocks new attempt → 409."""
        mock_sdk = _mock_sdk()
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
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

    def test_7_6_reintento_tras_pago_rechazado_crea_nuevo_pago(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """Rejected previous payment → new attempt creates a new Pago."""
        from features.payments.models import Pago
        import uuid

        pago_rechazado = Pago(
            pedido_id=sample_pedido.id,
            monto=Decimal("150.00"),
            forma_pago_codigo="MERCADOPAGO",
            idempotency_key=str(uuid.uuid4()),
            mp_status="rejected",
        )
        test_db_session.add(pago_rechazado)
        test_db_session.commit()

        mock_sdk = _mock_sdk(payment_status="approved", payment_id="mp_pay_retry")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json={
                    "pedido_id": sample_pedido.id,
                    "card_token": "tok_test_123",
                    "payment_method_id": "visa",
                    "installments": 1,
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440004",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        body = response.json()
        assert body["mp_status"] == "approved"


# ---------------------------------------------------------------------------
# POST /api/v1/pagos/webhook/mercadopago
# ---------------------------------------------------------------------------


class TestWebhook:
    def test_7_7_webhook_approved_confirma_pedido(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Format 1 webhook approved → 200 + order moves to CONFIRMADO + history entry added."""
        from features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        mock_sdk = _mock_sdk(
            payment_status="approved",
            external_reference=str(sample_pedido.id),
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                WEBHOOK_URL,
                json={"type": "payment", "data": {"id": "mp_pay_001"}},
            )

        assert response.status_code == 200

        test_db_session.expire_all()

        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == sample_pago.id)
        ).scalar_one()
        assert pago.mp_status == "approved"
        assert pago.mp_payment_id == "mp_pay_001"

        from features.orders.models import Pedido

        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "CONFIRMADO"

        historial = test_db_session.execute(
            sa_select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == sample_pedido.id,
                HistorialEstadoPedido.estado_nuevo_codigo == "CONFIRMADO",
            )
        ).scalar_one_or_none()
        assert historial is not None
        assert historial.estado_anterior_codigo == "PENDIENTE"
        assert historial.cambiado_por_id is None

    def test_7_8_webhook_rejected_pedido_sigue_pendiente(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Format 1 webhook rejected → 200 + order remains PENDIENTE + pago.mp_status=rejected."""
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="rejected",
            external_reference=str(sample_pedido.id),
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                WEBHOOK_URL,
                json={"type": "payment", "data": {"id": "mp_pay_002"}},
            )

        assert response.status_code == 200

        test_db_session.expire_all()

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == sample_pago.id)
        ).scalar_one()
        assert pago.mp_status == "rejected"

        from features.orders.models import Pedido

        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "PENDIENTE"

    def test_7_9_webhook_duplicado_no_duplica_historial(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Duplicate webhook for already-approved payment → 200, no extra history row."""
        from features.payments.models import Pago
        from features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select as sa_select

        # Simulate the first webhook having already been processed
        sample_pago.mp_payment_id = "mp_pay_dup"
        sample_pago.mp_status = "approved"
        test_db_session.commit()

        # Also put the order in CONFIRMADO (as it would be after first webhook)
        sample_pedido.estado_codigo = "CONFIRMADO"
        test_db_session.commit()

        mock_sdk = _mock_sdk(
            payment_status="approved",
            external_reference=str(sample_pedido.id),
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                WEBHOOK_URL,
                json={"type": "payment", "data": {"id": "mp_pay_dup"}},
            )

        assert response.status_code == 200

        test_db_session.expire_all()

        historial_count = (
            test_db_session.execute(
                sa_select(HistorialEstadoPedido).where(
                    HistorialEstadoPedido.pedido_id == sample_pedido.id,
                    HistorialEstadoPedido.estado_nuevo_codigo == "CONFIRMADO",
                )
            )
            .scalars()
            .all()
        )
        assert len(historial_count) == 0  # No CONFIRMADO entry was added

    def test_webhook_format2_old_ipn_body_confirma_pedido(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Format 2 (old IPN body with resource URL) → 200 + order moves to CONFIRMADO."""
        from features.orders.models import Pedido
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="approved",
            external_reference=str(sample_pedido.id),
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                WEBHOOK_URL,
                json={
                    "topic": "payment",
                    "resource": "https://api.mercadopago.com/v1/payments/999001",
                },
            )

        assert response.status_code == 200

        test_db_session.expire_all()

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == sample_pago.id)
        ).scalar_one()
        assert pago.mp_status == "approved"

        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "CONFIRMADO"

    def test_webhook_format3_classic_ipn_query_params_confirma_pedido(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Format 3 (classic IPN via query params, empty body) → 200 + order moves to CONFIRMADO."""
        from features.orders.models import Pedido
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="approved",
            external_reference=str(sample_pedido.id),
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                WEBHOOK_URL + "?topic=payment&id=mp_pay_fmt3",
            )

        assert response.status_code == 200

        test_db_session.expire_all()

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == sample_pago.id)
        ).scalar_one()
        assert pago.mp_status == "approved"

        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "CONFIRMADO"

    def test_webhook_payload_irreconocible_retorna_200_sin_efecto(
        self, client: TestClient, test_db_session: Session, sample_pedido, sample_pago
    ):
        """Unrecognised webhook payload → 200 with no side effects (silent discard)."""
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        response = client.post(
            WEBHOOK_URL,
            json={"action": "test.created", "foo": "bar"},
        )

        assert response.status_code == 200

        test_db_session.expire_all()
        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == sample_pago.id)
        ).scalar_one()
        assert pago.mp_status == "pending"  # unchanged


# ---------------------------------------------------------------------------
# GET /api/v1/pagos/pedido/{pedido_id}
# ---------------------------------------------------------------------------


class TestObtenerPagoPedido:
    def test_7_10_pago_existente_retorna_200(
        self, client: TestClient, auth_headers: dict, sample_pedido, sample_pago
    ):
        """Existing payment for own order → 200 + PagoRead."""
        response = client.get(
            f"{BASE_URL}/pedido/{sample_pedido.id}", headers=auth_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["pedido_id"] == sample_pedido.id
        assert body["mp_status"] == "pending"

    def test_7_11_pedido_sin_pagos_retorna_404(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """Order with no payments yet → 404."""
        response = client.get(
            f"{BASE_URL}/pedido/{sample_pedido.id}", headers=auth_headers
        )
        assert response.status_code == 404

    def test_7_12_pedido_ajeno_retorna_403(
        self, client: TestClient, otro_auth_headers: dict, sample_pedido, sample_pago
    ):
        """Payment check for another user's order → 403."""
        response = client.get(
            f"{BASE_URL}/pedido/{sample_pedido.id}", headers=otro_auth_headers
        )
        assert response.status_code == 403
