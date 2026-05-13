"""
End-to-end state flow tests (order-state-machine-fsm #16).

Tests cover:
  - Flujo completo: creación → confirmación automática → avance manual → entrega
  - Cancelación desde CONFIRMADO por PEDIDOS con motivo
  - Cancelación desde PENDIENTE por CLIENT sin motivo

Note: orders with items require PostgreSQL (ARRAY(Integer) in order_items).
These e2e tests use pedidos without items to run on SQLite — stock side-effects
are covered at repo + service level. Full e2e with stock requires pg_only.

Runner: cd backend && uv run pytest tests/integration/test_e2e_estado.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


ESTADO_URL = "/api/v1/pedidos/{pedido_id}/estado"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pedido_pendiente_via_db(test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido):
    """A minimal Pedido in PENDIENTE state (no items — SQLite compatible)."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("350.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def auth_headers_pedidos_e2e(client, test_db_session: Session, sample_roles):
    """Auth headers for a PEDIDOS role user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="pedidos_e2e@example.com",
        password_hash=hash_password("e2e_pw_123"),
        nombre="Gestor E2E",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "pedidos_e2e@example.com", "password": "e2e_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_admin_e2e(client, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="admin_e2e@example.com",
        password_hash=hash_password("admin_e2e_pw_123"),
        nombre="Admin E2E",
        apellido="Sistema",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_e2e@example.com", "password": "admin_e2e_pw_123"},
    )
    return {}


# ---------------------------------------------------------------------------
# E2E flows
# ---------------------------------------------------------------------------

class TestFlowEstados:

    def test_flow_confirmado_avanza_a_en_preparacion_en_camino_entregado(
        self, client: TestClient, auth_headers_pedidos_e2e,
        test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
    ):
        """
        Flow: CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO (PEDIDOS role).
        Each transition returns 200 with updated estado_codigo.
        """
        from features.orders.models import HistorialEstadoPedido, Pedido
        from sqlalchemy import select

        # Start in CONFIRMADO (simulating post-webhook)
        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("300.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        url = ESTADO_URL.format(pedido_id=pedido.id)

        # CONFIRMADO → EN_PREPARACION
        r1 = client.patch(url, json={"nuevo_estado": "EN_PREPARACION"}, headers=auth_headers_pedidos_e2e)
        assert r1.status_code == 200
        assert r1.json()["estado_codigo"] == "EN_PREPARACION"

        # EN_PREPARACION → EN_CAMINO
        r2 = client.patch(url, json={"nuevo_estado": "EN_CAMINO"}, headers=auth_headers_pedidos_e2e)
        assert r2.status_code == 200
        assert r2.json()["estado_codigo"] == "EN_CAMINO"

        # EN_CAMINO → ENTREGADO
        r3 = client.patch(url, json={"nuevo_estado": "ENTREGADO"}, headers=auth_headers_pedidos_e2e)
        assert r3.status_code == 200
        assert r3.json()["estado_codigo"] == "ENTREGADO"

        # Verify historial has 3 entries (one per transition)
        test_db_session.expire_all()
        historial = test_db_session.execute(
            select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == pedido.id,
            ).order_by(HistorialEstadoPedido.id)
        ).scalars().all()
        assert len(historial) == 3
        assert historial[-1].estado_nuevo_codigo == "ENTREGADO"

    def test_flow_cancelacion_admin_desde_confirmado_con_motivo(
        self, client: TestClient, auth_headers_admin_e2e,
        test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
    ):
        """
        ADMIN cancels CONFIRMADO with motivo → 200, historial with motivo.
        """
        from features.orders.models import HistorialEstadoPedido, Pedido
        from sqlalchemy import select

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("200.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        url = ESTADO_URL.format(pedido_id=pedido.id)
        r = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO", "motivo": "Problema con el proveedor"},
            headers=auth_headers_admin_e2e,
        )
        assert r.status_code == 200
        assert r.json()["estado_codigo"] == "CANCELADO"

        test_db_session.expire_all()
        historial = test_db_session.execute(
            select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == pedido.id,
                HistorialEstadoPedido.estado_nuevo_codigo == "CANCELADO",
            )
        ).scalar_one_or_none()
        assert historial is not None
        assert historial.motivo == "Problema con el proveedor"

    def test_flow_cancelacion_client_desde_pendiente_sin_motivo(
        self, client: TestClient, auth_headers,
        pedido_pendiente_via_db
    ):
        """
        CLIENT cancels PENDIENTE without motivo → 200, historial with motivo=NULL.
        """
        from features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        url = ESTADO_URL.format(pedido_id=pedido_pendiente_via_db.id)
        r = client.patch(url, json={"nuevo_estado": "CANCELADO"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["estado_codigo"] == "CANCELADO"

    def test_flow_admin_cancel_en_preparacion_requiere_motivo(
        self, client: TestClient, auth_headers_admin_e2e,
        test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
    ):
        """
        ADMIN cancels EN_PREPARACION: motivo required → 422 without, 200 with.
        """
        from features.orders.models import Pedido

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("200.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="EN_PREPARACION",
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        url = ESTADO_URL.format(pedido_id=pedido.id)

        # Without motivo → 422
        r_no_motivo = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO"},
            headers=auth_headers_admin_e2e,
        )
        assert r_no_motivo.status_code == 422

        # With motivo → 200
        r_con_motivo = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO", "motivo": "Cierre anticipado del local"},
            headers=auth_headers_admin_e2e,
        )
        assert r_con_motivo.status_code == 200
