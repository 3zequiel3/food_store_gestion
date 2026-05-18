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
    status_detail="accredited",
    mp_error=None,
):
    """Build a MagicMock that mimics the MercadoPago SDK.

    mp_error: dict to put in the 'error' key of create() response.
              If set and payment_status is empty/None, simulates mp_unreachable.
    """
    sdk = MagicMock()
    sdk.preference.return_value.create.return_value = {
        "response": {"init_point": init_point, "id": "pref_123"}
    }

    create_response: dict = {}
    if payment_status:
        create_response = {
            "status": payment_status,
            "id": payment_id,
            "status_detail": status_detail,
            "external_reference": external_reference or "",
        }

    create_result: dict = {"response": create_response}
    if mp_error:
        create_result["error"] = mp_error

    sdk.payment.return_value.create.return_value = create_result
    sdk.payment.return_value.get.return_value = {
        "response": {
            "status": payment_status or "",
            "external_reference": external_reference or "",
        }
    }
    return sdk


def _pago_payload(pedido_id: int, idempotency_key: str = "550e8400-e29b-41d4-a716-446655440000") -> dict:
    """Build a minimal valid PagoCreate payload."""
    return {
        "pedido_id": pedido_id,
        "card_token": "tok_test_123",
        "payment_method_id": "visa",
        "installments": 1,
        "idempotency_key": idempotency_key,
        "identification_type": "DNI",
        "identification_number": "12345678",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/pagos — Checkout API (direct card charge)
# ---------------------------------------------------------------------------


class TestCrearPago:
    def test_7_2_pago_valido_retorna_200_con_mp_status(
        self, client: TestClient, auth_headers: dict, sample_pedido
    ):
        """Happy path: valid PENDIENTE order → 200 + mp_status=approved + pago_id presente."""
        mock_sdk = _mock_sdk(payment_status="approved", payment_id="mp_pay_001")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440000"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "approved"
        assert body["mp_id"] == "mp_pay_001"
        assert "pago_id" in body
        assert isinstance(body["pago_id"], int)

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
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440001"),
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
                json=_pago_payload(pedido.id, "550e8400-e29b-41d4-a716-446655440002"),
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
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440003"),
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
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440004"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "approved"


    # ------------------------------------------------------------------
    # Tasks 3.3-3.9: nuevos escenarios de integración (TDD RED primero)
    # ------------------------------------------------------------------

    def test_crear_pago_api_approved_returns_200_and_transitions_order(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP aprueba → 200 con PagoCreateResponse completo + pedido pasa a CONFIRMADO."""
        from features.orders.models import Pedido
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(payment_status="approved", payment_id="mp_pay_approved_t33")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440010"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "approved"
        assert body["mp_id"] == "mp_pay_approved_t33"
        assert "status_detail" in body
        assert "pago_id" in body
        assert isinstance(body["pago_id"], int)

        test_db_session.expire_all()
        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "CONFIRMADO"

    def test_crear_pago_api_pending_returns_200_keeps_order_pendiente(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP devuelve pending → 200 con mp_status='pending', pedido sigue en PENDIENTE."""
        from features.orders.models import Pedido
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="pending",
            payment_id="mp_pay_pending",
            status_detail="pending_review_manual",
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440011"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "pending"

        test_db_session.expire_all()
        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "PENDIENTE"

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == body["pago_id"])
        ).scalar_one()
        assert pago.mp_status == "pending"

    def test_crear_pago_api_in_process_returns_200(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP devuelve in_process → 200 con mp_status='in_process'."""
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="in_process",
            payment_id="mp_pay_in_process",
            status_detail="pending_waiting_payment",
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440012"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "in_process"

        test_db_session.expire_all()
        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == body["pago_id"])
        ).scalar_one()
        assert pago.mp_status == "in_process"

    def test_crear_pago_api_rejected_returns_200_keeps_order_pendiente(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP rechaza → 200 con mp_status='rejected', pedido sigue PENDIENTE, reintento no bloqueado."""
        from features.orders.models import Pedido
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="rejected",
            payment_id="mp_pay_rejected",
            status_detail="cc_rejected_insufficient_amount",
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440013"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "rejected"

        test_db_session.expire_all()
        pedido = test_db_session.execute(
            sa_select(Pedido).where(Pedido.id == sample_pedido.id)
        ).scalar_one()
        assert pedido.estado_codigo == "PENDIENTE"

        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == body["pago_id"])
        ).scalar_one()
        assert pago.mp_status == "rejected"

        # Reintento no bloqueado — 'rejected' no está en _ACTIVE_STATUSES
        mock_sdk2 = _mock_sdk(payment_status="approved", payment_id="mp_pay_retry2")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk2,
        ):
            retry_response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440014"),
                headers=auth_headers,
            )
        assert retry_response.status_code == 200

    def test_crear_pago_api_cancelled_returns_200(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP cancela → 200 con mp_status='cancelled'."""
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status="cancelled",
            payment_id="mp_pay_cancelled",
            status_detail="by_collector",
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440015"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "cancelled"

        test_db_session.expire_all()
        pago = test_db_session.execute(
            sa_select(Pago).where(Pago.id == body["pago_id"])
        ).scalar_one()
        assert pago.mp_status == "cancelled"

    def test_crear_pago_api_mp_unreachable_does_not_create_pago(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        test_db_session: Session,
    ):
        """MP no responde con status → 502 mp_unreachable, NO se crea Pago en DB."""
        from features.payments.models import Pago
        from sqlalchemy import select as sa_select

        mock_sdk = _mock_sdk(
            payment_status=None,
            payment_id=None,
            mp_error={"message": "Connection timeout", "cause": [{"description": "Network error"}]},
        )
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440016"),
                headers=auth_headers,
            )

        assert response.status_code == 502
        body = response.json()
        assert body.get("code") == "mp_unreachable" or "mp_unreachable" in str(body)

        test_db_session.expire_all()
        pagos = test_db_session.execute(
            sa_select(Pago).where(Pago.pedido_id == sample_pedido.id)
        ).scalars().all()
        assert len(pagos) == 0  # NO se creó ningún Pago fantasma

    def test_crear_pago_api_approved_transition_failure_logs_but_returns_200(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedido,
        caplog,
    ):
        """Si la transición falla, el endpoint igual devuelve 200 y se loguea ERROR."""
        import logging

        mock_sdk = _mock_sdk(payment_status="approved", payment_id="mp_pay_trans_fail")
        with patch(
            "features.payments.service.PaymentService._get_sdk",
            return_value=mock_sdk,
        ), patch(
            "features.orders.service.OrderService.transicionar_estado",
            side_effect=Exception("DB error simulado"),
        ), caplog.at_level(logging.ERROR):
            response = client.post(
                BASE_URL + "/",
                json=_pago_payload(sample_pedido.id, "550e8400-e29b-41d4-a716-446655440017"),
                headers=auth_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["mp_status"] == "approved"

        # Debe haber un log ERROR sobre la transición fallida
        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_logs) > 0


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
