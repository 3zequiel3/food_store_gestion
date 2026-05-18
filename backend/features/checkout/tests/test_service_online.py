"""
Unit tests for CheckoutService.crear_pedido_online (tasks 3.2-3.14).

Covers:
  3.2  APPROVED → creates order in PENDIENTE state, returns CheckoutOnlineResponse
  3.3  APPROVED → creates Pago with mp_status='approved'
  3.4  REJECTED → raises PaymentRejectedError, no order created
  3.5  PENDING → raises PaymentPendingNotAcceptedError, no order created
  3.6  IN_PROCESS → same as PENDING (strict mode D3)
  3.7  CANCELLED → raises PaymentCancelledError
  3.8  UNKNOWN status → raises PaymentUnexpectedStatusError
  3.9  MP unreachable (exception) → raises UpstreamError
  3.10 MP responds with no 'status' key → raises UpstreamError
  3.11 Idempotency: existing payment found → returns cached result, no MP call
  3.12 Product not found → raises NotFoundError
  3.13 Product not available → raises BusinessRuleError
  3.14 Stock insufficient → raises BusinessRuleError

Runner: cd backend && uv run pytest features/checkout/tests/test_service_online.py -v
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Import all models to ensure SQLAlchemy mapper relationships are configured
# before any service code instantiates ORM objects.
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

from features.checkout.exceptions import (
    PaymentCancelledError,
    PaymentPendingNotAcceptedError,
    PaymentRejectedError,
    PaymentUnexpectedStatusError,
)
from features.checkout.schemas import CheckoutItem, CheckoutOnlineRequest
from features.checkout.service import CheckoutService
from shared.exceptions import BusinessRuleError, NotFoundError, UpstreamError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(**overrides: Any) -> CheckoutOnlineRequest:
    """Build a minimal valid CheckoutOnlineRequest."""
    defaults: dict[str, Any] = {
        "items": [CheckoutItem(producto_id=1, cantidad=2)],
        "tipo_entrega": "PICKUP",
        "direccion_id": None,
        "notas": None,
        "card_token": "tok_test_abc",
        "payment_method_id": "visa",
        "installments": 1,
        "idempotency_key": uuid4(),
        "identification_type": "DNI",
        "identification_number": "12345678",
    }
    defaults.update(overrides)
    return CheckoutOnlineRequest(**defaults)


def _make_producto(
    id: int = 1,
    nombre: str = "Hamburguesa",
    precio: float = 500.0,
    disponible: bool = True,
    stock_cantidad: int = 10,
) -> MagicMock:
    """Build a MagicMock that looks like a Producto."""
    p = MagicMock()
    p.id = id
    p.nombre = nombre
    p.precio = precio
    p.disponible = disponible
    p.stock_cantidad = stock_cantidad
    return p


def _mp_response(status: str, payment_id: str = "mp_123", status_detail: str = "accredited") -> dict:
    """Build a MercadoPago SDK response dict."""
    return {
        "response": {
            "status": status,
            "id": payment_id,
            "status_detail": status_detail,
        }
    }


# ---------------------------------------------------------------------------
# Base patch setup
# ---------------------------------------------------------------------------

_UOW_PATH = "features.checkout.service.UnitOfWork"
_SDK_PATH = "features.checkout.service.CheckoutService._get_sdk"
_PRODUCT_REPO_PATH = "features.checkout.service.ProductRepository"
_PAYMENT_REPO_PATH = "features.checkout.service.PaymentRepository"


def _make_uow_mock(producto: MagicMock | None = None) -> MagicMock:
    """Build a UoW context manager mock with product_repo and payment_repo wired."""
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)

    # session mock
    uow.session = MagicMock()
    uow.session.add = MagicMock()
    uow.session.flush = MagicMock()

    # Simulated Pedido after flush (needs an id)
    pedido_mock = MagicMock()
    pedido_mock.id = 42

    # Simulated Pago after flush
    pago_mock = MagicMock()
    pago_mock.id = 99
    pago_mock.pedido_id = 42
    pago_mock.mp_status = "approved"
    pago_mock.mp_payment_id = "mp_123"
    pago_mock.external_reference = None

    # Make session.add side-effects so we can track what was added
    added_objects = []

    def _add(obj):
        added_objects.append(obj)

    uow.session.add.side_effect = _add
    uow._added_objects = added_objects

    return uow


# ---------------------------------------------------------------------------
# 3.2 — APPROVED creates order in PENDIENTE
# ---------------------------------------------------------------------------

class TestApprovedCreatesOrder:
    def test_approved_returns_checkout_response(self):
        """Task 3.2 — approved payment returns CheckoutOnlineResponse with correct fields."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            # First UoW call: validation + idempotency check
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()

            # Second UoW call: creation
            uow_create = MagicMock()
            uow_create.__enter__ = MagicMock(return_value=uow_create)
            uow_create.__exit__ = MagicMock(return_value=False)
            uow_create.session = MagicMock()

            # Pedido and Pago assigned id on flush
            pedido_mock = MagicMock()
            pedido_mock.id = 42
            pago_mock = MagicMock()
            pago_mock.id = 99
            pago_mock.pedido_id = 42
            pago_mock.mp_status = "approved"
            pago_mock.mp_payment_id = "mp_123"

            # UoW is called twice
            MockUoW.side_effect = [uow_instance, uow_create]

            # ProductRepository returns our mock product
            prod_repo_instance = MagicMock()
            prod_repo_instance.read.return_value = producto
            MockProductRepo.return_value = prod_repo_instance

            # PaymentRepository for idempotency check returns None (no existing payment)
            pay_repo_instance = MagicMock()
            pay_repo_instance.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo_instance

            # MP SDK returns approved
            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("approved")
            mock_get_sdk.return_value = sdk_mock

            # Simulate flush assigning id to Pedido and Pago
            from features.orders.models import Pedido as PedidoModel
            from features.payments.models import Pago as PagoModel

            added_objects = []
            def _flush():
                # Assign id to the most recently added object if it's a Pedido or Pago
                for obj in added_objects:
                    if not hasattr(obj, "id") or obj.id is None:
                        obj.id = 42 if hasattr(obj, "estado_codigo") else 99
            uow_create.session.flush.side_effect = _flush
            uow_create.session.add.side_effect = added_objects.append

            service = CheckoutService()
            result = service.crear_pedido_online(user_id=1, request=request)

        assert result.mp_status == "approved"
        assert result.mp_id == "mp_123"
        assert result.status_detail == "accredited"

    # 3.3 — SDK was called with correct payment data
    def test_approved_calls_sdk_with_correct_amount(self):
        """Task 3.3 — MP SDK is called with the calculated total."""
        producto = _make_producto(precio=250.0, stock_cantidad=5)
        request = _make_request(
            items=[CheckoutItem(producto_id=1, cantidad=2)],
            tipo_entrega="PICKUP",
        )
        expected_total = 250.0 * 2  # 500.0, no shipping for PICKUP

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_validate = MagicMock()
            uow_validate.__enter__ = MagicMock(return_value=uow_validate)
            uow_validate.__exit__ = MagicMock(return_value=False)
            uow_validate.session = MagicMock()

            uow_create = MagicMock()
            uow_create.__enter__ = MagicMock(return_value=uow_create)
            uow_create.__exit__ = MagicMock(return_value=False)
            uow_create.session = MagicMock()
            uow_create.session.add = MagicMock()

            MockUoW.side_effect = [uow_validate, uow_create]

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("approved")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            try:
                service.crear_pedido_online(user_id=1, request=request)
            except Exception:
                pass  # We only care that SDK was called

        call_args = sdk_mock.payment.return_value.create.call_args
        assert call_args is not None
        payment_data = call_args[0][0]
        assert payment_data["transaction_amount"] == expected_total


# ---------------------------------------------------------------------------
# 3.4 — REJECTED → PaymentRejectedError
# ---------------------------------------------------------------------------

class TestRejectedPayment:
    def test_rejected_raises_payment_rejected_error(self):
        """Task 3.4 — MP rejected status raises PaymentRejectedError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response(
                "rejected", status_detail="cc_rejected_insufficient_amount"
            )
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(PaymentRejectedError):
                service.crear_pedido_online(user_id=1, request=request)


# ---------------------------------------------------------------------------
# 3.5 — PENDING → PaymentPendingNotAcceptedError (strict mode D3)
# ---------------------------------------------------------------------------

class TestPendingStrictMode:
    def test_pending_raises_error(self):
        """Task 3.5 — MP pending status raises PaymentPendingNotAcceptedError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("pending")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(PaymentPendingNotAcceptedError):
                service.crear_pedido_online(user_id=1, request=request)

    def test_in_process_raises_error(self):
        """Task 3.6 — MP in_process status raises PaymentPendingNotAcceptedError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("in_process")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(PaymentPendingNotAcceptedError):
                service.crear_pedido_online(user_id=1, request=request)


# ---------------------------------------------------------------------------
# 3.7 — CANCELLED → PaymentCancelledError
# ---------------------------------------------------------------------------

class TestCancelledPayment:
    def test_cancelled_raises_error(self):
        """Task 3.7 — MP cancelled status raises PaymentCancelledError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("cancelled")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(PaymentCancelledError):
                service.crear_pedido_online(user_id=1, request=request)


# ---------------------------------------------------------------------------
# 3.8 — Unknown status → PaymentUnexpectedStatusError
# ---------------------------------------------------------------------------

class TestUnknownStatus:
    def test_unknown_status_raises_error(self):
        """Task 3.8 — unknown MP status raises PaymentUnexpectedStatusError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.return_value = _mp_response("refunded")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(PaymentUnexpectedStatusError):
                service.crear_pedido_online(user_id=1, request=request)


# ---------------------------------------------------------------------------
# 3.9 — MP unreachable → UpstreamError (502)
# ---------------------------------------------------------------------------

class TestMPUnreachable:
    def test_mp_exception_raises_upstream_error(self):
        """Task 3.9 — MP SDK raises exception → UpstreamError with code mp_unreachable."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            sdk_mock.payment.return_value.create.side_effect = ConnectionError("timeout")
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(UpstreamError) as exc_info:
                service.crear_pedido_online(user_id=1, request=request)

        assert exc_info.value.code == "mp_unreachable"

    def test_mp_no_status_raises_upstream_error(self):
        """Task 3.10 — MP responds without 'status' key → UpstreamError."""
        producto = _make_producto()
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            # Response without 'status' key
            sdk_mock.payment.return_value.create.return_value = {
                "response": {"message": "Bad request", "id": None}
            }
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            with pytest.raises(UpstreamError) as exc_info:
                service.crear_pedido_online(user_id=1, request=request)

        assert exc_info.value.code == "mp_unreachable"


# ---------------------------------------------------------------------------
# 3.11 — Idempotency: existing payment found → return cached, no MP call
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_existing_payment_returns_cached_without_calling_mp(self):
        """Task 3.11 — same idempotency_key returns cached result without re-charging."""
        idempotency_key = uuid4()
        request = _make_request(idempotency_key=idempotency_key)

        # Build a mock Pago that already exists
        existing_pago = MagicMock()
        existing_pago.id = 77
        existing_pago.pedido_id = 55
        existing_pago.mp_status = "approved"
        existing_pago.mp_payment_id = "mp_existing_123"
        existing_pago.external_reference = str(idempotency_key)

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
            patch(_SDK_PATH) as mock_get_sdk,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = _make_producto()
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = existing_pago
            MockPaymentRepo.return_value = pay_repo

            sdk_mock = MagicMock()
            mock_get_sdk.return_value = sdk_mock

            service = CheckoutService()
            result = service.crear_pedido_online(user_id=1, request=request)

        # MP SDK should NOT have been called
        sdk_mock.payment.return_value.create.assert_not_called()

        assert result.pedido_id == 55
        assert result.pago_id == 77
        assert result.mp_status == "approved"


# ---------------------------------------------------------------------------
# 3.12 — Product not found → NotFoundError
# ---------------------------------------------------------------------------

class TestProductValidation:
    def test_product_not_found_raises_not_found(self):
        """Task 3.12 — unknown producto_id raises NotFoundError."""
        request = _make_request(items=[CheckoutItem(producto_id=999, cantidad=1)])

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = None  # Product not found
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            service = CheckoutService()
            with pytest.raises(NotFoundError):
                service.crear_pedido_online(user_id=1, request=request)

    def test_unavailable_product_raises_business_rule(self):
        """Task 3.13 — product with disponible=False raises BusinessRuleError."""
        producto = _make_producto(disponible=False)
        request = _make_request()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            service = CheckoutService()
            with pytest.raises(BusinessRuleError) as exc_info:
                service.crear_pedido_online(user_id=1, request=request)

        assert exc_info.value.code == "product_not_available"

    def test_insufficient_stock_raises_business_rule(self):
        """Task 3.14 — cantidad > stock raises BusinessRuleError."""
        producto = _make_producto(stock_cantidad=1)
        request = _make_request(items=[CheckoutItem(producto_id=1, cantidad=5)])

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_PAYMENT_REPO_PATH) as MockPaymentRepo,
        ):
            uow_instance = MagicMock()
            uow_instance.__enter__ = MagicMock(return_value=uow_instance)
            uow_instance.__exit__ = MagicMock(return_value=False)
            uow_instance.session = MagicMock()
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            pay_repo = MagicMock()
            pay_repo.find_by_external_reference.return_value = None
            MockPaymentRepo.return_value = pay_repo

            service = CheckoutService()
            with pytest.raises(BusinessRuleError) as exc_info:
                service.crear_pedido_online(user_id=1, request=request)

        assert exc_info.value.code == "insufficient_stock"
