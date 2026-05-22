"""
IDOR fix tests — delivery address ownership validation in checkout paths.

Security: a client-supplied `direccion_id` MUST be verified to belong to the
authenticated user before the order is created. Without this check, a user
could attach another user's saved address to their order (IDOR).

Pattern mirrored from orders/service.py D6:
  AddressRepository.find_by_id_and_user(direccion_id, user_id) → None
  → raise NotFoundError("Dirección no encontrada")  (404, anti-leak)

Paths covered:
  - CheckoutService.crear_pedido_delivery_efectivo  (POST /checkout/delivery-efectivo)
  - CheckoutService.crear_pedido_online             (POST /checkout/online, DELIVERY mode)

Runner:
  cd backend && uv run pytest tests/unit/test_checkout_idor_fix.py -v
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Bootstrap SQLAlchemy mapper before importing service/schemas.
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

from shared.exceptions import NotFoundError

# ── patch paths ───────────────────────────────────────────────────────────────

_UOW_PATH = "features.checkout.service.UnitOfWork"
_PRODUCT_REPO_PATH = "features.checkout.service.ProductRepository"
_ADDRESS_REPO_PATH = "features.checkout.service.AddressRepository"


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_producto(
    id: int = 1,
    nombre: str = "Burger",
    precio: float = 200.0,
    disponible: bool = True,
    stock_cantidad: int = 10,
) -> MagicMock:
    p = MagicMock()
    p.id = id
    p.nombre = nombre
    p.precio = precio
    p.disponible = disponible
    p.stock_cantidad = stock_cantidad
    p.ingredientes = []
    return p


def _make_uow_patch() -> MagicMock:
    """Return a UoW context-manager mock."""
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.session = MagicMock()
    uow.session.flush = MagicMock()
    return uow


def _delivery_efectivo_request(direccion_id: int = 5) -> Any:
    from features.checkout.schemas import CheckoutItem, CheckoutDeliveryEfectivoRequest

    return CheckoutDeliveryEfectivoRequest(
        items=[CheckoutItem(producto_id=1, cantidad=1)],
        direccion_id=direccion_id,
        notas=None,
    )


def _online_delivery_request() -> Any:
    from features.checkout.schemas import CheckoutOnlineRequest, CheckoutItem

    return CheckoutOnlineRequest(
        items=[CheckoutItem(producto_id=1, cantidad=1)],
        tipo_entrega="DELIVERY",
        direccion_id=99,
        card_token="tok_test",
        payment_method_id="visa",
        installments=1,
        identification_type="DNI",
        identification_number="12345678",
        idempotency_key="00000000-0000-0000-0000-000000000001",
        notas=None,
        payer_email="buyer@test.com",
    )


# ── delivery-efectivo path ────────────────────────────────────────────────────


class TestDeliveryEfectivoOwnershipGuard:
    """
    POST /checkout/delivery-efectivo — address ownership is enforced before the
    order is persisted. A direccion_id from another user must be rejected with
    the same error/status that orders/service.py raises (NotFoundError → 404).
    """

    def test_foreign_address_raises_not_found(self):
        """
        direccion_id that belongs to a DIFFERENT user → NotFoundError (404).
        AddressRepository.find_by_id_and_user returns None to signal
        'not found OR not yours' (anti-leak pattern from orders D6).
        """
        from features.checkout.service import CheckoutService

        producto = _make_producto()
        request = _delivery_efectivo_request(direccion_id=5)

        uow_instance = _make_uow_patch()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_ADDRESS_REPO_PATH) as MockAddressRepo,
        ):
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            # Simulate: address id=5 does NOT belong to user_id=1
            addr_repo = MagicMock()
            addr_repo.find_by_id_and_user.return_value = None
            MockAddressRepo.return_value = addr_repo

            service = CheckoutService()
            with pytest.raises(NotFoundError):
                service.crear_pedido_delivery_efectivo(user_id=1, request=request)

        # Verify the repo was called with the right arguments
        addr_repo.find_by_id_and_user.assert_called_once_with(5, 1)

    def test_own_address_is_accepted(self):
        """
        direccion_id that belongs to the authenticated user → order created (happy path).
        """
        from features.checkout.service import CheckoutService
        from features.orders.models import Pedido as PedidoModel

        producto = _make_producto()
        request = _delivery_efectivo_request(direccion_id=5)

        uow_instance = _make_uow_patch()

        def _add_side_effect(obj):
            if isinstance(obj, PedidoModel):
                obj.id = 77

        uow_instance.session.add.side_effect = _add_side_effect

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_ADDRESS_REPO_PATH) as MockAddressRepo,
        ):
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            # Simulate: address id=5 belongs to user_id=1
            mock_addr = MagicMock()
            addr_repo = MagicMock()
            addr_repo.find_by_id_and_user.return_value = mock_addr
            MockAddressRepo.return_value = addr_repo

            service = CheckoutService()
            result = service.crear_pedido_delivery_efectivo(user_id=1, request=request)

        assert result.pedido_id == 77


# ── online path (DELIVERY mode) ───────────────────────────────────────────────


class TestOnlineDeliveryOwnershipGuard:
    """
    POST /checkout/online with tipo_entrega=DELIVERY — address ownership must be
    enforced in the same centralised validation step (_validar_y_calcular_carrito).
    """

    def test_foreign_address_on_online_delivery_raises_not_found(self):
        """
        CheckoutOnlineRequest with tipo_entrega=DELIVERY and a direccion_id that
        belongs to another user → NotFoundError (404) before any MP call.
        """
        from features.checkout.service import CheckoutService

        producto = _make_producto()
        request = _online_delivery_request()

        uow_instance = _make_uow_patch()

        # Mock idempotency check to return None (no duplicate)
        payment_repo_mock = MagicMock()
        payment_repo_mock.find_by_external_reference.return_value = None

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_ADDRESS_REPO_PATH) as MockAddressRepo,
            patch("features.checkout.service.PaymentRepository") as MockPayRepo,
        ):
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            # Address does NOT belong to user_id=1
            addr_repo = MagicMock()
            addr_repo.find_by_id_and_user.return_value = None
            MockAddressRepo.return_value = addr_repo

            MockPayRepo.return_value = payment_repo_mock

            service = CheckoutService()
            with pytest.raises(NotFoundError):
                service.crear_pedido_online(user_id=1, request=request)

        addr_repo.find_by_id_and_user.assert_called_once_with(99, 1)

    def test_own_address_on_online_delivery_passes_validation(self):
        """
        CheckoutOnlineRequest with tipo_entrega=DELIVERY and a direccion_id
        that belongs to the authenticated user → validation passes.
        The test stops after MP call fails (no mock for MP) — we only care
        that the ownership check does NOT raise NotFoundError.
        """
        from features.checkout.service import CheckoutService

        producto = _make_producto()
        request = _online_delivery_request()

        uow_instance = _make_uow_patch()

        payment_repo_mock = MagicMock()
        payment_repo_mock.find_by_external_reference.return_value = None

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
            patch(_ADDRESS_REPO_PATH) as MockAddressRepo,
            patch("features.checkout.service.PaymentRepository") as MockPayRepo,
            patch("features.checkout.service.CheckoutService._get_sdk") as MockSdk,
        ):
            MockUoW.return_value = uow_instance

            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            # Address DOES belong to user_id=1
            mock_addr = MagicMock()
            addr_repo = MagicMock()
            addr_repo.find_by_id_and_user.return_value = mock_addr
            MockAddressRepo.return_value = addr_repo

            MockPayRepo.return_value = payment_repo_mock

            # MP call raises — that's fine; we only verify that the
            # NotFoundError from the ownership guard is NOT raised.
            MockSdk.return_value.payment.return_value.create.side_effect = (
                Exception("mp_not_mocked")
            )

            service = CheckoutService()
            # Must NOT raise NotFoundError (ownership OK). Any other exception is fine.
            try:
                service.crear_pedido_online(user_id=1, request=request)
            except NotFoundError:
                pytest.fail(
                    "NotFoundError raised for an address that belongs to the user — "
                    "ownership guard is too strict"
                )
            except Exception:
                pass  # MP or other downstream errors are expected in this mock setup

        addr_repo.find_by_id_and_user.assert_called_once_with(99, 1)
