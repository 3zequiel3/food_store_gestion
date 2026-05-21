"""
Integration tests for COCINA role in FSM transitions.

Tests that COCINA role can perform kitchen transitions (CONFIRMADO→EN_PREPARACION,
EN_PREPARACION→TERMINADO) and is rejected for non-kitchen transitions.

Also verifies that PEDIDOS and ADMIN roles still work for kitchen transitions
(backward compatibility).

Runner: cd backend && uv run pytest tests/integration/test_cocina_fsm.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shared.security import hash_password

TRANSICIONAR_URL = "/api/v1/pedidos/{pedido_id}/transicionar"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_headers_pedidos(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a PEDIDOS user."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="pedidos_fsm@example.com",
        password_hash=hash_password("pedidos_pw_123"),
        nombre="Gestor",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "pedidos_fsm@example.com", "password": "pedidos_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_admin(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="admin_fsm@example.com",
        password_hash=hash_password("admin_fsm_pw"),
        nombre="Admin",
        apellido="FSM",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "admin_fsm@example.com", "password": "admin_fsm_pw"},
    )
    return {}


@pytest.fixture
def auth_headers_cocina(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a COCINA user."""
    from features.users.models import Usuario, UsuarioRol
    from features.catalog.models import Rol

    # Ensure COCINA role exists
    cocina_role = test_db_session.execute(
        pytest.importorskip("sqlalchemy").select(Rol).where(Rol.codigo == "COCINA")
    ).scalar_one_or_none()
    if not cocina_role:
        cocina_role = Rol(id=5, codigo="COCINA", descripcion="Cocinero")
        test_db_session.add(cocina_role)
        test_db_session.commit()

    user = Usuario(
        email="cocina_fsm@example.com",
        password_hash=hash_password("cocina_pw_123"),
        nombre="Cocina",
        apellido="FSM",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=5))  # COCINA
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "cocina_fsm@example.com", "password": "cocina_pw_123"},
    )
    return {}


@pytest.fixture
def pedido_confirmado(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in CONFIRMADO state."""
    from features.orders.models import Pedido

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
    return pedido


@pytest.fixture
def pedido_en_preparacion(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in EN_PREPARACION state."""
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
    return pedido


@pytest.fixture
def pedido_terminado(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in TERMINADO state."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="TERMINADO",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


# ---------------------------------------------------------------------------
# Tests — COCINA allowed transitions
# ---------------------------------------------------------------------------


class TestCocinaAllowedTransitions:
    """COCINA can perform kitchen transitions."""

    def test_cocina_can_confirm_to_preparacion(
        self, client: TestClient, auth_headers_cocina, pedido_confirmado
    ):
        """COCINA role can transition CONFIRMADO→EN_PREPARACION."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_PREPARACION"},
            headers=auth_headers_cocina,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_anterior"] == "CONFIRMADO"
        assert body["estado_nuevo"] == "EN_PREPARACION"

    def test_cocina_can_preparacion_to_terminado(
        self, client: TestClient, auth_headers_cocina, pedido_en_preparacion
    ):
        """COCINA role can transition EN_PREPARACION→TERMINADO."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_en_preparacion.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "TERMINADO"},
            headers=auth_headers_cocina,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_anterior"] == "EN_PREPARACION"
        assert body["estado_nuevo"] == "TERMINADO"


# ---------------------------------------------------------------------------
# Tests — backward compatibility (PEDIDOS and ADMIN still work)
# ---------------------------------------------------------------------------


class TestBackwardCompatibilityKitchenTransitions:
    """PEDIDOS and ADMIN can still perform kitchen transitions."""

    def test_pedidos_still_allowed_kitchen_transitions(
        self, client: TestClient, auth_headers_pedidos, pedido_confirmado
    ):
        """PEDIDOS can still do CONFIRMADO→EN_PREPARACION and EN_PREPARACION→TERMINADO."""
        # CONFIRMADO→EN_PREPARACION
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_PREPARACION"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "EN_PREPARACION"

        # Now EN_PREPARACION→TERMINADO
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "TERMINADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "TERMINADO"

    def test_admin_still_allowed_kitchen_transitions(
        self, client: TestClient, auth_headers_admin, pedido_confirmado
    ):
        """ADMIN can still do CONFIRMADO→EN_PREPARACION and EN_PREPARACION→TERMINADO."""
        # CONFIRMADO→EN_PREPARACION
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_PREPARACION"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "EN_PREPARACION"

        # Now EN_PREPARACION→TERMINADO
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "TERMINADO"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "TERMINADO"


# ---------------------------------------------------------------------------
# Tests — COCINA forbidden transitions
# ---------------------------------------------------------------------------


class TestCocinaForbiddenTransitions:
    """COCINA role is rejected for non-kitchen transitions."""

    def test_cocina_forbidden_dispatch(
        self, client: TestClient, auth_headers_cocina, pedido_terminado
    ):
        """COCINA role REJECTED (403) for TERMINADO→ENTREGADO."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "ENTREGADO"},
            headers=auth_headers_cocina,
        )
        assert response.status_code == 403

    def test_cocina_forbidden_cancel(
        self, client: TestClient, auth_headers_cocina, pedido_confirmado
    ):
        """COCINA role REJECTED (403) for CONFIRMADO→CANCELADO_ADMIN."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN", "motivo": "Test"},
            headers=auth_headers_cocina,
        )
        assert response.status_code == 403
