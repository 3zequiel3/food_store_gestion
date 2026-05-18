"""
Unit tests for PaymentRepository — payments-non-approved-as-data change.

Tests run against SQLite in-memory via the conftest fixtures.

Runner: cd backend && uv run pytest tests/unit/test_payment_repository.py -xvs
"""

from __future__ import annotations

from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def _formas_pago(test_db_session: Session):
    """Seed TARJETA payment method for repository tests."""
    from features.catalog.models import FormaPago

    forma = FormaPago(codigo="TARJETA", descripcion="Tarjeta de crédito/débito", habilitada=True)
    test_db_session.add(forma)
    test_db_session.commit()
    return forma


@pytest.fixture
def _pedido(test_db_session: Session, sample_user, sample_estados_pedido, _formas_pago):
    """A minimal PENDIENTE order for payment repository tests."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("150.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="TARJETA",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


class TestCreatePagoMpStatus:
    """create_pago debe persistir el mp_status real, no hardcodeado 'pending'."""

    def test_create_pago_con_mp_status_rejected(self, test_db_session: Session, _pedido):
        """create_pago(..., mp_status='rejected') inserta con mp_status='rejected', no 'pending'."""
        from features.payments.repository import PaymentRepository

        repo = PaymentRepository(test_db_session)
        pago = repo.create_pago(
            pedido_id=_pedido.id,
            monto=Decimal("150.00"),
            forma_pago_codigo="TARJETA",
            idempotency_key=str(uuid.uuid4()),
            mp_status="rejected",
        )
        test_db_session.commit()

        assert pago.mp_status == "rejected"

    def test_create_pago_con_mp_status_approved(self, test_db_session: Session, _pedido):
        """create_pago(..., mp_status='approved') inserta con mp_status='approved'."""
        from features.payments.repository import PaymentRepository

        repo = PaymentRepository(test_db_session)
        pago = repo.create_pago(
            pedido_id=_pedido.id,
            monto=Decimal("150.00"),
            forma_pago_codigo="TARJETA",
            idempotency_key=str(uuid.uuid4()),
            mp_status="approved",
        )
        test_db_session.commit()

        assert pago.mp_status == "approved"

    def test_create_pago_sin_mp_status_default_pending(self, test_db_session: Session, _pedido):
        """create_pago(...) sin mp_status usa 'pending' como default (retrocompat)."""
        from features.payments.repository import PaymentRepository

        repo = PaymentRepository(test_db_session)
        pago = repo.create_pago(
            pedido_id=_pedido.id,
            monto=Decimal("150.00"),
            forma_pago_codigo="TARJETA",
            idempotency_key=str(uuid.uuid4()),
        )
        test_db_session.commit()

        assert pago.mp_status == "pending"
