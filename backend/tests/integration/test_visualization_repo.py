"""
Unit tests for OrderRepository visualization methods (#17).

Tests:
  - list_with_filter: ownership, no-filter, pagination
  - count_with_filter: consistency with list_with_filter
  - get_pedido_completo: user_id=None (admin), user_id mismatch (None returned)
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from features.orders.repository import OrderRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(test_db_session: Session):
    return OrderRepository(test_db_session)


@pytest.fixture
def user_a(test_db_session: Session, sample_roles):
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="usera@example.com",
        password_hash=hash_password("pass"),
        nombre="User",
        apellido="Alpha",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=4))
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def user_b(test_db_session: Session, sample_roles):
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="userb@example.com",
        password_hash=hash_password("pass"),
        nombre="User",
        apellido="Beta",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=4))
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def pedidos_a(test_db_session: Session, user_a, sample_estados_pedido, sample_formas_pago):
    """3 Pedidos for user_a."""
    from features.orders.models import Pedido

    pedidos = [
        Pedido(
            user_id=user_a.id,
            total=Decimal(f"{i + 1}00.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="EFECTIVO",
            estado_codigo="PENDIENTE",
        )
        for i in range(3)
    ]
    for p in pedidos:
        test_db_session.add(p)
    test_db_session.commit()
    for p in pedidos:
        test_db_session.refresh(p)
    return pedidos


@pytest.fixture
def pedidos_b(test_db_session: Session, user_b, sample_estados_pedido, sample_formas_pago):
    """2 Pedidos for user_b."""
    from features.orders.models import Pedido

    pedidos = [
        Pedido(
            user_id=user_b.id,
            total=Decimal(f"{i + 4}00.00"),
            costo_envio=Decimal("50.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        for i in range(2)
    ]
    for p in pedidos:
        test_db_session.add(p)
    test_db_session.commit()
    for p in pedidos:
        test_db_session.refresh(p)
    return pedidos


# ---------------------------------------------------------------------------
# list_with_filter
# ---------------------------------------------------------------------------

class TestListWithFilter:
    def test_filtra_por_user_id(self, repo, pedidos_a, pedidos_b, user_a):
        """With user_id=user_a.id, returns only user_a's pedidos."""
        rows = repo.list_with_filter(
            user_id=user_a.id,
            estado=None, desde=None, hasta=None, q=None,
            page=1, limit=20,
        )
        ids = {p.id for p, _ in rows}
        assert ids == {p.id for p in pedidos_a}

    def test_user_id_none_no_filtra(self, repo, pedidos_a, pedidos_b):
        """With user_id=None, returns all pedidos."""
        rows = repo.list_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=None,
            page=1, limit=20,
        )
        assert len(rows) == 5

    def test_filtra_por_estado(self, repo, pedidos_a, pedidos_b):
        """Filter by estado=CONFIRMADO returns only CONFIRMADO pedidos."""
        rows = repo.list_with_filter(
            user_id=None,
            estado="CONFIRMADO", desde=None, hasta=None, q=None,
            page=1, limit=20,
        )
        assert len(rows) == 2
        assert all(p.estado_codigo == "CONFIRMADO" for p, _ in rows)

    def test_paginacion_offset(self, repo, pedidos_a, pedidos_b):
        """page=2, limit=2 returns items 3-4 (or 3-5)."""
        rows_p1 = repo.list_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=None,
            page=1, limit=2,
        )
        rows_p2 = repo.list_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=None,
            page=2, limit=2,
        )
        ids_p1 = {p.id for p, _ in rows_p1}
        ids_p2 = {p.id for p, _ in rows_p2}
        assert ids_p1.isdisjoint(ids_p2)

    def test_orden_creado_en_desc(self, repo, pedidos_a):
        """Results ordered by creado_en DESC."""
        rows = repo.list_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=None,
            page=1, limit=20,
        )
        fechas = [p.creado_en for p, _ in rows]
        assert fechas == sorted(fechas, reverse=True)

    def test_q_numerico_filtra_por_id(self, repo, pedidos_a):
        """q='<id>' returns only that pedido."""
        target = pedidos_a[0]
        rows = repo.list_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=str(target.id),
            page=1, limit=20,
        )
        assert len(rows) == 1
        assert rows[0][0].id == target.id


# ---------------------------------------------------------------------------
# count_with_filter
# ---------------------------------------------------------------------------

class TestCountWithFilter:
    def test_count_consistente_con_list(self, repo, pedidos_a, pedidos_b, user_a):
        """count_with_filter == len(list_with_filter) for the same filters."""
        count = repo.count_with_filter(
            user_id=user_a.id,
            estado=None, desde=None, hasta=None, q=None,
        )
        rows = repo.list_with_filter(
            user_id=user_a.id,
            estado=None, desde=None, hasta=None, q=None,
            page=1, limit=100,
        )
        assert count == len(rows) == 3

    def test_count_none_no_filtra(self, repo, pedidos_a, pedidos_b):
        """count with user_id=None returns total of all pedidos."""
        count = repo.count_with_filter(
            user_id=None,
            estado=None, desde=None, hasta=None, q=None,
        )
        assert count == 5


# ---------------------------------------------------------------------------
# get_pedido_completo
# ---------------------------------------------------------------------------

class TestGetPedidoCompleto:
    def test_user_id_none_no_filtra_ownership(
        self, repo, test_db_session, user_a, pedidos_a
    ):
        """With user_id=None, returns pedido regardless of ownership."""
        target = pedidos_a[0]
        result = repo.get_pedido_completo(target.id, user_id=None)
        assert result is not None
        assert result.id == target.id

    def test_user_id_correcto_retorna_pedido(self, repo, user_a, pedidos_a):
        """get_pedido_completo(user_id=owner) returns the pedido."""
        target = pedidos_a[0]
        result = repo.get_pedido_completo(target.id, user_id=user_a.id)
        assert result is not None
        assert result.id == target.id

    def test_user_id_mismatch_retorna_none(self, repo, user_b, pedidos_a):
        """get_pedido_completo with wrong user_id returns None."""
        target = pedidos_a[0]
        result = repo.get_pedido_completo(target.id, user_id=user_b.id)
        assert result is None

    def test_pedido_inexistente_retorna_none(self, repo, sample_estados_pedido):
        """Non-existent id returns None regardless of user_id."""
        result = repo.get_pedido_completo(99999, user_id=None)
        assert result is None
