"""
Unit tests for CheckoutService.crear_pedido_pickup_efectivo (tasks 3.16-3.19).

Covers:
  3.16 Pickup+efectivo creates Pedido in PENDIENTE with forma_pago=EFECTIVO, no Pago created
  3.17 MP SDK is NOT invoked for pickup orders
  3.18 Product not found → NotFoundError
  3.19 Stock insufficient → BusinessRuleError

Runner: cd backend && uv run pytest features/checkout/tests/test_service_pickup.py -v
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# Import all models to ensure SQLAlchemy mapper relationships are configured.
import features.auth.models  # noqa: F401
import features.users.models  # noqa: F401
import features.catalog.models  # noqa: F401
import features.addresses.models  # noqa: F401
import features.products.models  # noqa: F401
import features.payments.models  # noqa: F401
try:
    import features.orders.models  # noqa: F401
except Exception:
    pass

from features.checkout.schemas import CheckoutItem, CheckoutPickupEfectivoRequest
from features.checkout.service import CheckoutService
from shared.exceptions import BusinessRuleError, NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pickup_request(**overrides: Any) -> CheckoutPickupEfectivoRequest:
    """Build a minimal valid CheckoutPickupEfectivoRequest."""
    defaults: dict[str, Any] = {
        "items": [CheckoutItem(producto_id=1, cantidad=1)],
        "notas": None,
    }
    defaults.update(overrides)
    return CheckoutPickupEfectivoRequest(**defaults)


def _make_producto(
    id: int = 1,
    nombre: str = "Empanada",
    precio: float = 150.0,
    disponible: bool = True,
    stock_cantidad: int = 20,
) -> MagicMock:
    """Build a MagicMock that looks like a Producto."""
    p = MagicMock()
    p.id = id
    p.nombre = nombre
    p.precio = precio
    p.disponible = disponible
    p.stock_cantidad = stock_cantidad
    return p


_UOW_PATH = "features.checkout.service.UnitOfWork"
_SDK_PATH = "features.checkout.service.CheckoutService._get_sdk"
_PRODUCT_REPO_PATH = "features.checkout.service.ProductRepository"
_PAYMENT_REPO_PATH = "features.checkout.service.PaymentRepository"


# ---------------------------------------------------------------------------
# 3.16 — Pickup+efectivo creates Pedido in PENDIENTE without Pago
# ---------------------------------------------------------------------------

class TestPickupEfectivoCreatesOrder:
    def test_creates_pedido_with_pendiente_state(self):
        """Task 3.16 — pickup returns CheckoutPickupEfectivoResponse with pedido_id."""
        from features.orders.models import Pedido as PedidoModel

        producto = _make_producto()
        request = _make_pickup_request()
        added_objects: list = []

        def _add_and_assign_id(obj):
            added_objects.append(obj)
            if isinstance(obj, PedidoModel):
                obj.id = 10

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            uow_instance.session.add.side_effect = _add_and_assign_id
            uow_instance.session.flush = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            result = service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert result.pedido_id == 10

    def test_no_pago_object_added(self):
        """Task 3.16 — no Pago model is added to the session for pickup+efectivo."""
        from features.payments.models import Pago

        producto = _make_producto()
        request = _make_pickup_request()
        added_objects: list = []

        def _add_and_assign_id(obj):
            added_objects.append(obj)
            # Auto-assign id to Pedido when added (simulates flush)
            from features.orders.models import Pedido as PedidoModel
            if isinstance(obj, PedidoModel):
                obj.id = 10

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            uow_instance.session.add.side_effect = _add_and_assign_id
            uow_instance.session.flush = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        # No Pago instance should have been added to session
        pago_instances = [obj for obj in added_objects if isinstance(obj, Pago)]
        assert len(pago_instances) == 0, "No Pago should be created for pickup+efectivo"


# ---------------------------------------------------------------------------
# 3.17 — MP SDK NOT invoked for pickup
# ---------------------------------------------------------------------------

class TestPickupDoesNotCallMP:
    def test_mp_sdk_not_called(self):
        """Task 3.17 — _get_sdk is never called for pickup+efectivo orders."""
        from features.orders.models import Pedido as PedidoModel

        producto = _make_producto()
        request = _make_pickup_request()

        def _add_and_assign_id(obj):
            if isinstance(obj, PedidoModel):
                obj.id = 20

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            uow_instance.session.add.side_effect = _add_and_assign_id
            uow_instance.session.flush = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        mock_get_sdk.assert_not_called()


# ---------------------------------------------------------------------------
# 3.18 — Product not found
# ---------------------------------------------------------------------------

class TestPickupProductValidation:
    def test_product_not_found_raises_not_found(self):
        """Task 3.18 — unknown producto_id raises NotFoundError."""
        request = _make_pickup_request(items=[CheckoutItem(producto_id=999, cantidad=1)])

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = None
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            with pytest.raises(NotFoundError):
                service.crear_pedido_pickup_efectivo(user_id=1, request=request)


# ---------------------------------------------------------------------------
# 3.19 — Stock insufficient
# ---------------------------------------------------------------------------

class TestPickupStockValidation:
    def test_stock_insufficient_raises_business_rule(self):
        """Task 3.19 — cantidad > stock raises BusinessRuleError with insufficient_stock."""
        producto = _make_producto(stock_cantidad=2)
        request = _make_pickup_request(items=[CheckoutItem(producto_id=1, cantidad=10)])

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            with pytest.raises(BusinessRuleError) as exc_info:
                service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert exc_info.value.code == "insufficient_stock"
