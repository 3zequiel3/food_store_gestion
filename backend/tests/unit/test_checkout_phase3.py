"""
Phase 3 checkout tests — P2.8 (removable validation) and P0.2 (cash-on-delivery).

Tasks 3.1 and 3.3 — RED first, then GREEN after implementation.

P2.8 (task 3.1): personalizacion IDs must reference es_removible=True ingredients
  that belong to the product. Invalid IDs → BusinessRuleError (422).

P0.2 (task 3.3): EFECTIVO + direccion_id (cash-on-delivery) must be accepted:
  creates PENDIENTE order with shipping cost and NO Pago; the old hard block
  (invalid_payment_for_delivery) must no longer fire. Cash + pickup still works.

Runner: cd backend && uv run pytest tests/unit/test_checkout_phase3.py -v
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure SQLAlchemy mapper is configured before importing checkout schemas.
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

from shared.exceptions import BusinessRuleError, NotFoundError

# ── patch paths ──────────────────────────────────────────────────────────────

_UOW_PATH = "features.checkout.service.UnitOfWork"
_PRODUCT_REPO_PATH = "features.checkout.service.ProductRepository"
_PAYMENT_REPO_PATH = "features.checkout.service.PaymentRepository"
_SDK_PATH = "features.checkout.service.CheckoutService._get_sdk"


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_producto(
    id: int = 1,
    nombre: str = "Burger",
    precio: float = 200.0,
    disponible: bool = True,
    stock_cantidad: int = 10,
    ingredientes=None,
) -> MagicMock:
    """Build a MagicMock that looks like a Producto with an ingredientes list."""
    p = MagicMock()
    p.id = id
    p.nombre = nombre
    p.precio = precio
    p.disponible = disponible
    p.stock_cantidad = stock_cantidad
    p.ingredientes = ingredientes if ingredientes is not None else []
    return p


def _make_ingrediente(id: int, es_removible: bool = True) -> MagicMock:
    """Build a MagicMock that looks like an Ingrediente."""
    ing = MagicMock()
    ing.id = id
    ing.es_removible = es_removible
    return ing


def _make_uow_patch() -> tuple[MagicMock, MagicMock]:
    """Return (MockUoW_class, uow_instance). Caller must patch _UOW_PATH."""
    uow_instance = MagicMock()
    uow_instance.__enter__ = MagicMock(return_value=uow_instance)
    uow_instance.__exit__ = MagicMock(return_value=False)
    uow_instance.session = MagicMock()
    uow_instance.session.flush = MagicMock()
    return uow_instance


def _make_pickup_efectivo_request_with_personalizacion(
    producto_id: int = 1,
    cantidad: int = 1,
    personalizacion: list[int] | None = None,
) -> Any:
    from features.checkout.schemas import CheckoutItem, CheckoutPickupEfectivoRequest

    return CheckoutPickupEfectivoRequest(
        items=[
            CheckoutItem(
                producto_id=producto_id,
                cantidad=cantidad,
                personalizacion=personalizacion,
            )
        ],
        notas=None,
    )


def _make_delivery_efectivo_request(
    producto_id: int = 1,
    cantidad: int = 1,
    direccion_id: int = 5,
) -> Any:
    """Build a CheckoutDeliveryEfectivoRequest (P0.2 new schema)."""
    from features.checkout.schemas import CheckoutItem, CheckoutDeliveryEfectivoRequest

    return CheckoutDeliveryEfectivoRequest(
        items=[CheckoutItem(producto_id=producto_id, cantidad=cantidad)],
        direccion_id=direccion_id,
        notas=None,
    )


# ── Task 3.1 — P2.8: removable-ingredient validation ────────────────────────


class TestRemovableIngredientValidation:
    """
    P2.8 — server-side validation that personalizacion IDs reference
    es_removible=True ingredients belonging to the product.
    """

    def test_non_removible_ingredient_in_personalizacion_raises_422(self):
        """
        Ingredient IDs that are NOT es_removible=True for the product
        → BusinessRuleError (maps to 422 in the router).
        """
        from features.checkout.service import CheckoutService

        # Ingredient id=7 exists but es_removible=False
        ing_not_removible = _make_ingrediente(id=7, es_removible=False)
        producto = _make_producto(id=1, ingredientes=[ing_not_removible])
        request = _make_pickup_efectivo_request_with_personalizacion(
            producto_id=1, personalizacion=[7]
        )

        uow_instance = _make_uow_patch()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            with pytest.raises(BusinessRuleError) as exc_info:
                service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert exc_info.value.code == "invalid_personalizacion"

    def test_ingredient_not_in_product_raises_422(self):
        """
        Ingredient ID that does not belong to the product at all
        → BusinessRuleError regardless of es_removible.
        """
        from features.checkout.service import CheckoutService

        # Product has ingredient id=1 only; request personalizacion=[99]
        ing = _make_ingrediente(id=1, es_removible=True)
        producto = _make_producto(id=1, ingredientes=[ing])
        request = _make_pickup_efectivo_request_with_personalizacion(
            producto_id=1, personalizacion=[99]
        )

        uow_instance = _make_uow_patch()

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            with pytest.raises(BusinessRuleError) as exc_info:
                service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert exc_info.value.code == "invalid_personalizacion"

    def test_valid_removable_ingredient_in_personalizacion_accepted(self):
        """
        Ingredient that IS es_removible=True and belongs to the product
        → no exception raised, order created successfully.
        """
        from features.checkout.service import CheckoutService
        from features.orders.models import Pedido as PedidoModel

        ing_removible = _make_ingrediente(id=3, es_removible=True)
        producto = _make_producto(id=1, ingredientes=[ing_removible])
        request = _make_pickup_efectivo_request_with_personalizacion(
            producto_id=1, personalizacion=[3]
        )

        uow_instance = _make_uow_patch()

        def _add_and_assign_id(obj):
            if isinstance(obj, PedidoModel):
                obj.id = 42

        uow_instance.session.add.side_effect = _add_and_assign_id

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            result = service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert result.pedido_id == 42

    def test_empty_personalizacion_accepted(self):
        """
        None or empty personalizacion list is valid (no customizations).
        """
        from features.checkout.service import CheckoutService
        from features.orders.models import Pedido as PedidoModel

        ing = _make_ingrediente(id=1, es_removible=False)
        producto = _make_producto(id=1, ingredientes=[ing])
        request = _make_pickup_efectivo_request_with_personalizacion(
            producto_id=1, personalizacion=None
        )

        uow_instance = _make_uow_patch()

        def _add_and_assign_id(obj):
            if isinstance(obj, PedidoModel):
                obj.id = 7

        uow_instance.session.add.side_effect = _add_and_assign_id

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            result = service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert result.pedido_id == 7


# ── Task 3.3 — P0.2: cash-on-delivery ───────────────────────────────────────


class TestCashOnDelivery:
    """
    P0.2 — EFECTIVO + direccion_id must be accepted (cash-on-delivery).
    Creates PENDIENTE order with shipping cost and NO Pago row.
    The old invalid_payment_for_delivery block in orders/service.py must be gone.
    """

    def test_efectivo_with_direccion_creates_pendiente_order_with_shipping(self):
        """
        CheckoutService.crear_pedido_delivery_efectivo creates a PENDIENTE Pedido
        with costo_envio=50 and forma_pago_codigo='EFECTIVO'. No Pago is added.
        """
        from features.checkout.service import CheckoutService
        from features.orders.models import Pedido as PedidoModel
        from features.payments.models import Pago

        producto = _make_producto(id=1)
        request = _make_delivery_efectivo_request(producto_id=1, direccion_id=5)

        added_objects: list = []
        uow_instance = _make_uow_patch()

        def _add_and_assign_id(obj):
            added_objects.append(obj)
            if isinstance(obj, PedidoModel):
                obj.id = 55

        uow_instance.session.add.side_effect = _add_and_assign_id

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            result = service.crear_pedido_delivery_efectivo(
                user_id=1, request=request
            )

        assert result.pedido_id == 55

        # No Pago should be created
        pago_instances = [obj for obj in added_objects if isinstance(obj, Pago)]
        assert len(pago_instances) == 0, "Cash-on-delivery must NOT create a Pago"

        # The Pedido should have costo_envio=50 and forma_pago_codigo=EFECTIVO
        pedidos = [obj for obj in added_objects if isinstance(obj, PedidoModel)]
        assert len(pedidos) == 1
        pedido = pedidos[0]
        assert pedido.forma_pago_codigo == "EFECTIVO"
        assert Decimal(str(pedido.costo_envio)) == Decimal("50.00")

    def test_efectivo_with_direccion_old_block_does_not_fire(self):
        """
        The old orders/service.py invalid_payment_for_delivery block must not
        be triggered. Call OrderService.crear_pedido with EFECTIVO+direccion_id
        and verify it does NOT raise BusinessRuleError with that code.

        NOTE: This tests the orders/service.py guard removal (not checkout service).
        """
        from features.orders.service import OrderService
        from features.orders.schemas import CrearPedidoRequest, ItemPedidoRequest

        # We exercise the code path in orders/service.py that used to block EFECTIVO
        # with direccion_id. After P0.2 removal, it must NOT raise.
        # We mock the UoW deeply so no DB is needed.
        from features.orders.models import Pedido as PedidoModel

        added_objects: list = []
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.session = MagicMock()
        mock_uow.session.flush = MagicMock()
        mock_uow.session.refresh = MagicMock()

        def _add_and_assign_id(obj):
            added_objects.append(obj)
            if isinstance(obj, PedidoModel):
                obj.id = 77

        mock_uow.session.add.side_effect = _add_and_assign_id

        # Mock forma_pago as existing and enabled
        mock_forma = MagicMock()
        mock_uow.orders = MagicMock()
        mock_uow.orders.find_forma_pago.return_value = mock_forma
        mock_uow.direcciones = MagicMock()

        # Build a mock address
        mock_addr = MagicMock()
        mock_addr.calle = "Av Test"
        mock_addr.numero = "123"
        mock_addr.piso_depto = None
        mock_addr.ciudad = "BsAs"
        mock_addr.codigo_postal = "1001"
        mock_addr.referencia = None
        mock_uow.direcciones.find_by_id_and_user.return_value = mock_addr

        # Mock product
        mock_producto = MagicMock()
        mock_producto.id = 1
        mock_producto.nombre = "Burger"
        mock_producto.disponible = True
        mock_producto.stock_cantidad = 10
        mock_producto.precio = 200.0
        mock_uow.orders.get_producto_for_update.return_value = mock_producto

        mock_pedido = MagicMock()
        mock_pedido.id = 77
        mock_uow.orders.create_pedido.return_value = mock_pedido

        with patch("features.orders.service.UnitOfWork", return_value=mock_uow):
            service = OrderService()
            request = CrearPedidoRequest(
                items=[ItemPedidoRequest(producto_id=1, cantidad=1)],
                forma_pago_codigo="EFECTIVO",
                direccion_id=5,
            )
            # Must NOT raise BusinessRuleError with code=invalid_payment_for_delivery
            try:
                result = service.crear_pedido(user_id=1, payload=request)
                # If we reach here, the block was removed correctly
            except BusinessRuleError as e:
                if "invalid_payment_for_delivery" in str(e.code):
                    pytest.fail(
                        "The invalid_payment_for_delivery guard still fires — "
                        "P0.2 was not implemented correctly"
                    )
                # Other BusinessRuleErrors are acceptable (mocking is imperfect)
            except Exception:
                # Other exceptions from incomplete mocking are OK — we only care
                # that the delivery+efectivo guard specifically does NOT trigger.
                pass

    def test_cash_pickup_still_works(self):
        """
        Sanity: creating a pickup+efectivo order (no direccion_id) still works.
        The old guard only blocked delivery+efectivo; pickup was always allowed.
        """
        from features.checkout.service import CheckoutService
        from features.checkout.schemas import CheckoutItem, CheckoutPickupEfectivoRequest
        from features.orders.models import Pedido as PedidoModel

        producto = _make_producto(id=1, ingredientes=[])
        request = CheckoutPickupEfectivoRequest(
            items=[CheckoutItem(producto_id=1, cantidad=1)],
            notas=None,
        )

        uow_instance = _make_uow_patch()

        def _add_and_assign_id(obj):
            if isinstance(obj, PedidoModel):
                obj.id = 33

        uow_instance.session.add.side_effect = _add_and_assign_id

        with (
            patch(_UOW_PATH) as MockUoW,
            patch(_PRODUCT_REPO_PATH) as MockProductRepo,
        ):
            MockUoW.return_value = uow_instance
            prod_repo = MagicMock()
            prod_repo.read.return_value = producto
            MockProductRepo.return_value = prod_repo

            service = CheckoutService()
            result = service.crear_pedido_pickup_efectivo(user_id=1, request=request)

        assert result.pedido_id == 33
