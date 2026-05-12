"""
Integration tests for OrderRepository extensions — order-state-machine-fsm #16.

Tests:
  - get_pedido_for_update
  - create_historial_transicion (con/sin motivo)
  - decrement_stock_for_items
  - restore_stock_for_items

Runner: cd backend && uv run pytest tests/integration/test_order_repository_fsm.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.shared.exceptions import BusinessRuleError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(test_db_session: Session):
    """OrderRepository bound to the test session."""
    from backend.features.orders.repository import OrderRepository
    return OrderRepository(test_db_session)


@pytest.fixture
def pedido_pendiente(test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido):
    """A bare Pedido in PENDIENTE state (no items — used for repo-level tests)."""
    from backend.features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def producto_con_stock(test_db_session: Session):
    """A product with stock=10."""
    from backend.features.products.models import Producto

    p = Producto(
        nombre="Producto FSM Test",
        precio=Decimal("100.00"),
        stock_cantidad=10,
        disponible=True,
    )
    test_db_session.add(p)
    test_db_session.commit()
    test_db_session.refresh(p)
    return p


@pytest.fixture
def detalle_item(pedido_pendiente, producto_con_stock):
    """
    A lightweight DetallePedido-like object for stock tests.

    order_items uses ARRAY(Integer) which SQLite cannot create. We simulate
    a DetallePedido using a simple namespace so repo methods can access
    .producto_id and .cantidad without hitting SQLite.
    """
    from types import SimpleNamespace
    return SimpleNamespace(
        pedido_id=pedido_pendiente.id,
        producto_id=producto_con_stock.id,
        cantidad=3,
    )


# ---------------------------------------------------------------------------
# get_pedido_for_update
# ---------------------------------------------------------------------------

class TestGetPedidoForUpdate:

    def test_get_pedido_for_update_returns_pedido(self, repo, pedido_pendiente):
        """Returns the Pedido instance with correct fields."""
        pedido = repo.get_pedido_for_update(pedido_pendiente.id)

        assert pedido is not None
        assert pedido.id == pedido_pendiente.id
        assert pedido.estado_codigo == "PENDIENTE"
        assert pedido.user_id == pedido_pendiente.user_id

    def test_get_pedido_for_update_returns_none_si_no_existe(self, repo):
        """Returns None for a non-existent id."""
        result = repo.get_pedido_for_update(999999)
        assert result is None


# ---------------------------------------------------------------------------
# create_historial_transicion (con/sin motivo)
# ---------------------------------------------------------------------------

class TestCreateHistorialTransicion:

    def test_create_historial_transicion_acepta_motivo(
        self, repo, test_db_session: Session, pedido_pendiente, sample_user
    ):
        """Historial row is persisted with motivo when provided."""
        from backend.features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        historial = repo.create_historial_transicion(
            pedido_id=pedido_pendiente.id,
            estado_anterior_codigo="PENDIENTE",
            estado_nuevo_codigo="CANCELADO",
            actor_id=sample_user.id,
            motivo="Cliente canceló por error",
        )

        test_db_session.commit()

        row = test_db_session.execute(
            select(HistorialEstadoPedido).where(HistorialEstadoPedido.id == historial.id)
        ).scalar_one()

        assert row.motivo == "Cliente canceló por error"
        assert row.estado_anterior_codigo == "PENDIENTE"
        assert row.estado_nuevo_codigo == "CANCELADO"
        assert row.cambiado_por_id == sample_user.id

    def test_create_historial_transicion_sin_motivo_persiste_null(
        self, repo, test_db_session: Session, pedido_pendiente, sample_user
    ):
        """Historial row persisted without motivo keeps motivo=NULL."""
        from backend.features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        historial = repo.create_historial_transicion(
            pedido_id=pedido_pendiente.id,
            estado_anterior_codigo="PENDIENTE",
            estado_nuevo_codigo="CONFIRMADO",
            actor_id=None,  # SISTEMA
        )

        test_db_session.commit()

        row = test_db_session.execute(
            select(HistorialEstadoPedido).where(HistorialEstadoPedido.id == historial.id)
        ).scalar_one()

        assert row.motivo is None
        assert row.cambiado_por_id is None


# ---------------------------------------------------------------------------
# decrement_stock_for_items
# ---------------------------------------------------------------------------

class TestDecrementStockForItems:

    def test_decrement_stock_for_items_actualiza_stock(
        self, repo, test_db_session: Session, detalle_item, producto_con_stock
    ):
        """Stock decreases by item.cantidad after decrement."""
        from backend.features.products.models import Producto
        from sqlalchemy import select

        repo.decrement_stock_for_items([detalle_item])
        test_db_session.commit()

        producto = test_db_session.execute(
            select(Producto).where(Producto.id == producto_con_stock.id)
        ).scalar_one()

        assert producto.stock_cantidad == 7  # 10 - 3

    def test_decrement_stock_for_items_falla_si_stock_insuficiente(
        self, repo, test_db_session: Session, pedido_pendiente
    ):
        """BusinessRuleError when stock would go negative."""
        from types import SimpleNamespace
        from backend.features.products.models import Producto

        producto_poco_stock = Producto(
            nombre="Producto Escaso",
            precio=Decimal("10.00"),
            stock_cantidad=1,
            disponible=True,
        )
        test_db_session.add(producto_poco_stock)
        test_db_session.commit()
        test_db_session.refresh(producto_poco_stock)

        item = SimpleNamespace(
            pedido_id=pedido_pendiente.id,
            producto_id=producto_poco_stock.id,
            cantidad=5,
        )

        with pytest.raises(BusinessRuleError, match="Stock insuficiente"):
            repo.decrement_stock_for_items([item])


# ---------------------------------------------------------------------------
# restore_stock_for_items
# ---------------------------------------------------------------------------

class TestRestoreStockForItems:

    def test_restore_stock_for_items_actualiza_stock(
        self, repo, test_db_session: Session, detalle_item, producto_con_stock
    ):
        """Stock increases by item.cantidad after restore."""
        from backend.features.products.models import Producto
        from sqlalchemy import select

        # Simulate previously decremented stock
        producto_con_stock.stock_cantidad = 7
        test_db_session.commit()

        repo.restore_stock_for_items([detalle_item])
        test_db_session.commit()

        producto = test_db_session.execute(
            select(Producto).where(Producto.id == producto_con_stock.id)
        ).scalar_one()

        assert producto.stock_cantidad == 10  # 7 + 3
