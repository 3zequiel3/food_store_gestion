"""
Integration tests for OrderService extensions — order-state-machine-fsm #16.

Tests cover:
  - transicionar_estado() backward compatibility (regression, BLOQUEANTE)
  - transicionar_estado() stock side-effects
  - avanzar_estado() validations and delegation

Runner: cd backend && uv run pytest tests/integration/test_order_service_fsm.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def order_service():
    from features.orders.service import OrderService

    return OrderService()


@pytest.fixture
def producto(test_db_session: Session):
    """Product with stock=10."""
    from features.products.models import Producto

    p = Producto(
        nombre="Producto Servicio Test",
        precio=Decimal("50.00"),
        stock_cantidad=10,
        disponible=True,
    )
    test_db_session.add(p)
    test_db_session.commit()
    test_db_session.refresh(p)
    return p


@pytest.fixture
def pedido_pendiente_sin_items(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in PENDIENTE state — no items (for backward-compat and simple tests)."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("100.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedido_con_item(
    test_db_session: Session,
    sample_user,
    sample_formas_pago,
    sample_estados_pedido,
    producto,
):
    """
    A Pedido in PENDIENTE state with one DetallePedido-like item.

    NOTE: order_items uses ARRAY(Integer) which SQLite cannot create.
    We therefore attach a simple namespace to the pedido so service tests
    can trigger stock side-effects without inserting into order_items.

    The service loads items via selectinload(Pedido.items). Since SQLite
    can't create the order_items table, we bypass by monkey-patching the
    items relationship on the returned Pedido instance.
    """
    from types import SimpleNamespace
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("500.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)

    # Simulate a DetallePedido with cantidad=3
    fake_item = SimpleNamespace(
        pedido_id=pedido.id,
        producto_id=producto.id,
        cantidad=3,
    )
    # Monkey-patch items so transicionar_estado can access them
    object.__setattr__(pedido, "_fake_items", [fake_item])
    return pedido, fake_item


# ---------------------------------------------------------------------------
# Task 5.1 — Regression test (BLOQUEANTE)
# ---------------------------------------------------------------------------


class TestTransicionarEstadoRegression:
    """
    Regression: the existing webhook call signature must keep working
    after all extensions to transicionar_estado().
    """

    def test_webhook_transicion_pendiente_a_confirmado_sigue_funcionando(
        self, order_service, test_db_session: Session, pedido_pendiente_sin_items
    ):
        """
        PaymentService calls transicionar_estado(pedido_id, 'PENDIENTE', 'CONFIRMADO', actor_id=None).
        This exact call must succeed after extending the method (backwards compat).
        """
        from features.orders.models import HistorialEstadoPedido, Pedido
        from sqlalchemy import select

        pedido_id = pedido_pendiente_sin_items.id

        pedido_actualizado, historial_item = order_service.transicionar_estado(
            pedido_id=pedido_id,
            estado_anterior="PENDIENTE",
            estado_nuevo="CONFIRMADO",
            actor_id=None,
        )

        assert pedido_actualizado.estado_codigo == "CONFIRMADO"
        assert pedido_actualizado.id == pedido_id

        # W1: transicionar_estado now returns the freshly inserted historial.
        assert historial_item.id > 0
        assert historial_item.estado_anterior_codigo == "PENDIENTE"
        assert historial_item.estado_nuevo_codigo == "CONFIRMADO"
        assert historial_item.cambiado_por_id is None

        # Verify historial was persisted in DB (extra paranoid check)
        historial = test_db_session.execute(
            select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == pedido_id,
                HistorialEstadoPedido.estado_nuevo_codigo == "CONFIRMADO",
            )
        ).scalar_one_or_none()
        assert historial is not None
        assert historial.id == historial_item.id  # same row, no race
        assert historial.estado_anterior_codigo == "PENDIENTE"
        assert historial.cambiado_por_id is None
        assert historial.motivo is None

    def test_transicionar_estado_idempotencia_409(
        self, order_service, test_db_session: Session, pedido_pendiente_sin_items
    ):
        """Calling with wrong estado_anterior raises InvalidStateTransitionError (409)."""
        from shared.exceptions import InvalidStateTransitionError

        # Pedido is PENDIENTE — calling with CONFIRMADO as anterior raises 409
        with pytest.raises(InvalidStateTransitionError):
            order_service.transicionar_estado(
                pedido_id=pedido_pendiente_sin_items.id,
                estado_anterior="CONFIRMADO",
                estado_nuevo="EN_PREPARACION",
                actor_id=None,
            )

    # ── C2 hardening: lock-time re-check of ownership + RBAC ────────────────

    def test_transicionar_estado_sin_actor_roles_mantiene_path_sistema(
        self, order_service, pedido_pendiente_sin_items
    ):
        """SISTEMA path (actor_roles=None, used by the payment webhook) skips
        the lock-time ownership/RBAC checks. Legacy behavior preserved."""
        from shared.exceptions import InvalidStateTransitionError

        # estado_anterior mismatch still raises 409 — the SISTEMA-only guard.
        with pytest.raises(InvalidStateTransitionError):
            order_service.transicionar_estado(
                pedido_id=pedido_pendiente_sin_items.id,
                estado_anterior="CONFIRMADO",  # wrong on purpose
                estado_nuevo="EN_PREPARACION",
                actor_id=None,
                actor_roles=None,
            )

    def test_transicionar_estado_client_ownership_rechecked_in_lock(
        self, order_service, pedido_pendiente_sin_items, sample_user
    ):
        """
        C2: A CLIENT actor whose user_id does not match the locked pedido
        gets NotFoundError (not InvalidStateTransitionError), even when
        invoked directly against transicionar_estado.
        """
        from shared.exceptions import NotFoundError

        intruder_id = sample_user.id + 9999  # any non-owner id

        with pytest.raises(NotFoundError):
            order_service.transicionar_estado(
                pedido_id=pedido_pendiente_sin_items.id,
                estado_anterior="PENDIENTE",
                estado_nuevo="CANCELADO_CLIENTE",
                actor_id=intruder_id,
                actor_roles={"CLIENT"},
            )

    def test_transicionar_estado_rbac_rechecked_in_lock(
        self, order_service, pedido_pendiente_sin_items, sample_user
    ):
        """
        C2: validate_transition runs against the LOCKED state. A CLIENT
        cannot do PENDIENTE → CANCELADO_ADMIN (FSM allows it, RBAC restricts
        it to ADMIN/PEDIDOS), so ForbiddenError (403) wins over the 409 that
        the old code path would have produced if estado_anterior matched.
        """
        from shared.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            order_service.transicionar_estado(
                pedido_id=pedido_pendiente_sin_items.id,
                estado_anterior="PENDIENTE",
                estado_nuevo="CANCELADO_ADMIN",
                actor_id=sample_user.id,
                actor_roles={"CLIENT"},
            )


# ---------------------------------------------------------------------------
# Task 5.4-5.9 — Stock side-effects in transicionar_estado
# ---------------------------------------------------------------------------


class TestTransicionarEstadoStockSideEffects:
    def test_transicionar_estado_pendiente_a_confirmado_decrementa_stock(
        self, order_service, test_db_session: Session, pedido_con_item, producto
    ):
        """PENDIENTE → CONFIRMADO: stock decrements by item.cantidad."""
        from features.products.models import Producto
        from sqlalchemy import select
        import unittest.mock as mock

        pedido, fake_item = pedido_con_item

        # Patch the repo's load of items inside the UoW
        original_transicionar = order_service.transicionar_estado

        def patched_transicionar(
            pedido_id, estado_anterior, estado_nuevo, actor_id=None, motivo=None
        ):
            from features.orders.service import OrderService
            from features.orders.repository import OrderRepository
            from shared.unit_of_work import UnitOfWork
            from shared.exceptions import NotFoundError, InvalidStateTransitionError

            with UnitOfWork() as uow:
                uow.register_repository("orders", OrderRepository(uow.session))

                pedido_locked = uow.orders.get_pedido_for_update(pedido_id)
                if pedido_locked is None:
                    raise NotFoundError(f"Pedido no encontrado: id={pedido_id}")
                if pedido_locked.estado_codigo != estado_anterior:
                    raise InvalidStateTransitionError(
                        f"Transición inválida: el pedido está en '{pedido_locked.estado_codigo}', "
                        f"se esperaba '{estado_anterior}'"
                    )

                # Use fake items for stock
                if (estado_anterior, estado_nuevo) == ("PENDIENTE", "CONFIRMADO"):
                    uow.orders.decrement_stock_for_items([fake_item])

                pedido_locked.estado_codigo = estado_nuevo
                uow.session.flush()
                uow.orders.create_historial_transicion(
                    pedido_id=pedido_id,
                    estado_anterior_codigo=estado_anterior,
                    estado_nuevo_codigo=estado_nuevo,
                    actor_id=actor_id,
                    motivo=motivo,
                )
                uow.session.refresh(pedido_locked)
                return pedido_locked

        with mock.patch.object(
            order_service, "transicionar_estado", side_effect=patched_transicionar
        ):
            resultado = order_service.transicionar_estado(
                pedido_id=pedido.id,
                estado_anterior="PENDIENTE",
                estado_nuevo="CONFIRMADO",
                actor_id=None,
            )

        test_db_session.expire_all()
        p = test_db_session.execute(
            select(Producto).where(Producto.id == producto.id)
        ).scalar_one()
        assert p.stock_cantidad == 7  # 10 - 3

    def test_transicionar_estado_pendiente_a_cancelado_no_toca_stock(
        self,
        order_service,
        test_db_session: Session,
        pedido_pendiente_sin_items,
        sample_producto_disponible,
    ):
        """PENDIENTE → CANCELADO: stock not touched (never decremented)."""
        from features.products.models import Producto
        from sqlalchemy import select

        stock_inicial = sample_producto_disponible.stock_cantidad

        order_service.transicionar_estado(
            pedido_id=pedido_pendiente_sin_items.id,
            estado_anterior="PENDIENTE",
            estado_nuevo="CANCELADO",
            actor_id=None,
        )

        test_db_session.expire_all()
        p = test_db_session.execute(
            select(Producto).where(Producto.id == sample_producto_disponible.id)
        ).scalar_one()
        assert p.stock_cantidad == stock_inicial  # unchanged


# ---------------------------------------------------------------------------
# Task 5.10 — Idempotencia (already covered in regression, but explicit)
# ---------------------------------------------------------------------------


class TestTransicionarEstadoIdempotencia:
    def test_transicionar_estado_second_call_409(
        self, order_service, test_db_session: Session, pedido_pendiente_sin_items
    ):
        """Second identical call raises 409 — idempotent guard."""
        from shared.exceptions import InvalidStateTransitionError

        # First call succeeds
        order_service.transicionar_estado(
            pedido_id=pedido_pendiente_sin_items.id,
            estado_anterior="PENDIENTE",
            estado_nuevo="CONFIRMADO",
        )

        # Second call with same expected state raises 409
        with pytest.raises(InvalidStateTransitionError):
            order_service.transicionar_estado(
                pedido_id=pedido_pendiente_sin_items.id,
                estado_anterior="PENDIENTE",
                estado_nuevo="CONFIRMADO",
            )


# ---------------------------------------------------------------------------
# Fixtures for avanzar_estado tests
# ---------------------------------------------------------------------------


@pytest.fixture
def user_pedidos(test_db_session: Session, sample_roles):
    """A user with PEDIDOS role."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="pedidos@example.com",
        password_hash=hash_password("pedidos_pw_123"),
        nombre="Gestor",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def user_admin(test_db_session: Session, sample_roles):
    """A user with ADMIN role."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="admin@example.com",
        password_hash=hash_password("admin_pw_123"),
        nombre="Admin",
        apellido="Sistema",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def pedido_confirmado(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido already in CONFIRMADO state."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("300.00"),
        costo_envio=Decimal("50.00"),
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
        total=Decimal("300.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="EN_PREPARACION",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


# ---------------------------------------------------------------------------
# Tests for avanzar_estado
# ---------------------------------------------------------------------------


class TestAvanzarEstado:
    def test_avanzar_estado_rechaza_confirmado_explicit(
        self,
        order_service,
        test_db_session: Session,
        sample_user,
        pedido_pendiente_sin_items,
    ):
        """avanzar_estado rejects CONFIRMADO with BusinessRuleError — D5 second defense."""
        from shared.exceptions import BusinessRuleError

        with pytest.raises(
            BusinessRuleError, match="CONFIRMADO solo se setea automáticamente"
        ):
            order_service.avanzar_estado(
                user_id=sample_user.id,
                pedido_id=pedido_pendiente_sin_items.id,
                nuevo_estado="CONFIRMADO",
                motivo=None,
            )

    def test_avanzar_estado_pedido_no_existe_404(self, order_service, sample_user):
        """Non-existent pedido_id raises NotFoundError (404)."""
        from shared.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            order_service.avanzar_estado(
                user_id=sample_user.id,
                pedido_id=999999,
                nuevo_estado="CANCELADO",
                motivo=None,
            )

    def test_avanzar_estado_client_no_dueno_404(
        self,
        order_service,
        test_db_session: Session,
        sample_user,
        sample_roles,
        pedido_pendiente_sin_items,
    ):
        """CLIENT trying to act on a pedido they don't own gets 404 (anti-leak, D13)."""
        from features.users.models import Usuario, UsuarioRol
        from shared.security import hash_password
        from shared.exceptions import NotFoundError

        # Create another CLIENT user — doesn't own the pedido
        otro_client = Usuario(
            email="otro_client@example.com",
            password_hash=hash_password("client_pw_123"),
            nombre="Otro",
            apellido="Client",
            is_active=True,
        )
        test_db_session.add(otro_client)
        test_db_session.flush()
        test_db_session.add(UsuarioRol(user_id=otro_client.id, role_id=4))  # CLIENT
        test_db_session.commit()
        test_db_session.refresh(otro_client)

        with pytest.raises(NotFoundError):
            order_service.avanzar_estado(
                user_id=otro_client.id,
                pedido_id=pedido_pendiente_sin_items.id,  # owned by sample_user
                nuevo_estado="CANCELADO",
                motivo=None,
            )

    def test_avanzar_estado_pedidos_opera_sobre_pedido_ajeno_ok(
        self,
        order_service,
        test_db_session: Session,
        user_pedidos,
        pedido_pendiente_sin_items,
    ):
        """PEDIDOS can cancel any order regardless of ownership."""
        resultado = order_service.avanzar_estado(
            user_id=user_pedidos.id,
            pedido_id=pedido_pendiente_sin_items.id,
            nuevo_estado="CANCELADO",
            motivo=None,
        )
        assert resultado.estado_codigo == "CANCELADO"

    def test_avanzar_estado_fsm_invalida_422(
        self,
        order_service,
        test_db_session: Session,
        user_pedidos,
        pedido_pendiente_sin_items,
    ):
        """Transition not allowed by FSM raises BusinessRuleError."""
        from shared.exceptions import BusinessRuleError

        # PENDIENTE → TERMINADO is not a valid FSM transition
        with pytest.raises(BusinessRuleError):
            order_service.avanzar_estado(
                user_id=user_pedidos.id,
                pedido_id=pedido_pendiente_sin_items.id,
                nuevo_estado="TERMINADO",
                motivo=None,
            )

    def test_avanzar_estado_rol_insuficiente_403(
        self, order_service, test_db_session: Session, sample_user, pedido_confirmado
    ):
        """CLIENT cannot move CONFIRMADO → EN_PREPARACION — ForbiddenError (403)."""
        from shared.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            order_service.avanzar_estado(
                user_id=sample_user.id,
                pedido_id=pedido_confirmado.id,
                nuevo_estado="EN_PREPARACION",
                motivo=None,
            )

    def test_avanzar_estado_motivo_obligatorio_en_cancel_desde_confirmado_422(
        self, order_service, test_db_session: Session, user_pedidos, pedido_confirmado
    ):
        """Cancelling CONFIRMADO without motivo raises BusinessRuleError (D7)."""
        from shared.exceptions import BusinessRuleError

        with pytest.raises(BusinessRuleError, match="motivo es obligatorio"):
            order_service.avanzar_estado(
                user_id=user_pedidos.id,
                pedido_id=pedido_confirmado.id,
                nuevo_estado="CANCELADO_ADMIN",
                motivo=None,
            )

    def test_avanzar_estado_motivo_solo_espacios_es_invalido(
        self, order_service, test_db_session: Session, user_pedidos, pedido_confirmado
    ):
        """motivo with only whitespace is treated as missing (D7)."""
        from shared.exceptions import BusinessRuleError

        with pytest.raises(BusinessRuleError, match="motivo es obligatorio"):
            order_service.avanzar_estado(
                user_id=user_pedidos.id,
                pedido_id=pedido_confirmado.id,
                nuevo_estado="CANCELADO_ADMIN",
                motivo="   ",
            )

    def test_avanzar_estado_motivo_opcional_en_cancel_desde_pendiente(
        self,
        order_service,
        test_db_session: Session,
        sample_user,
        pedido_pendiente_sin_items,
    ):
        """Cancelling PENDIENTE without motivo is OK — motivo=NULL in historial."""
        from features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        resultado = order_service.avanzar_estado(
            user_id=sample_user.id,
            pedido_id=pedido_pendiente_sin_items.id,
            nuevo_estado="CANCELADO",
            motivo=None,
        )
        assert resultado.estado_codigo == "CANCELADO"

        historial = test_db_session.execute(
            select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == pedido_pendiente_sin_items.id,
                HistorialEstadoPedido.estado_nuevo_codigo == "CANCELADO",
            )
        ).scalar_one_or_none()
        assert historial is not None
        assert historial.motivo is None

    def test_avanzar_estado_pedidos_no_puede_cancel_desde_en_preparacion_403(
        self,
        order_service,
        test_db_session: Session,
        user_pedidos,
        pedido_en_preparacion,
    ):
        """PEDIDOS (without ADMIN) cannot cancel EN_PREPARACION — RN-RB08."""
        from shared.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            order_service.avanzar_estado(
                user_id=user_pedidos.id,
                pedido_id=pedido_en_preparacion.id,
                nuevo_estado="CANCELADO_ADMIN",
                motivo="algún motivo",
            )

    def test_avanzar_estado_con_motivo_valido_confirma_a_cancelado(
        self, order_service, test_db_session: Session, user_pedidos, pedido_confirmado
    ):
        """PEDIDOS can cancel CONFIRMADO with valid motivo — state changes, historial recorded."""
        from features.orders.models import HistorialEstadoPedido
        from sqlalchemy import select

        resultado = order_service.avanzar_estado(
            user_id=user_pedidos.id,
            pedido_id=pedido_confirmado.id,
            nuevo_estado="CANCELADO_ADMIN",
            motivo="Stock agotado inesperadamente",
        )
        assert resultado.estado_codigo == "CANCELADO_ADMIN"

        historial = test_db_session.execute(
            select(HistorialEstadoPedido).where(
                HistorialEstadoPedido.pedido_id == pedido_confirmado.id,
                HistorialEstadoPedido.estado_nuevo_codigo == "CANCELADO_ADMIN",
            )
        ).scalar_one_or_none()
        assert historial is not None
        assert historial.motivo == "Stock agotado inesperadamente"
        assert historial.cambiado_por_id == user_pedidos.id

    def test_avanzar_estado_admin_puede_cancelar_en_preparacion(
        self, order_service, test_db_session: Session, user_admin, pedido_en_preparacion
    ):
        """ADMIN can cancel EN_PREPARACION with motivo."""
        resultado = order_service.avanzar_estado(
            user_id=user_admin.id,
            pedido_id=pedido_en_preparacion.id,
            nuevo_estado="CANCELADO_ADMIN",
            motivo="Pedido problemático",
        )
        assert resultado.estado_codigo == "CANCELADO_ADMIN"
