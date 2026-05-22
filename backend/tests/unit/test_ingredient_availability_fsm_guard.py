"""
Unit tests — Tasks 6.11–6.14: FSM availability guard (D6b).

The guard is invoked from avanzar_estado BEFORE validate_transition,
only for CONFIRMADO→EN_PREPARACION and EN_PREPARACION→TERMINADO.

Design D6b:
- An order is BLOCKED if ANY line requires an ingredient with activo=False
  that is NOT excluded in that line's personalizacion.
- If the activo=False ingredient is excluded in ALL lines that use it → allowed.
- Two-line order: line A excludes, line B requires → BLOCKED (order-level).
- Block lifts when activo=True (guard re-reads activo each call).
- Guard does NOT intervene on non-kitchen transitions (e.g. cancellation).

Implementation rule: the guard lives in the SERVICE LAYER (orders/service.py),
not in state_machine.py (which stays pure/no-DB). Tested here by patching the
order and ingredient data so no DB is needed for these unit tests.

Runner: cd backend && uv run pytest tests/unit/test_ingredient_availability_fsm_guard.py -xvs
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — build fake ORM objects mimicking the eager-loaded structure
# ---------------------------------------------------------------------------


def _make_ingrediente(id_: int, nombre: str, activo: bool) -> MagicMock:
    ing = MagicMock()
    ing.id = id_
    ing.nombre = nombre
    ing.activo = activo
    return ing


def _make_producto(ingredientes: list) -> MagicMock:
    prod = MagicMock()
    prod.ingredientes = ingredientes
    return prod


def _make_detalle(
    *,
    producto_ingredientes: list,
    personalizacion: list | None = None,
) -> MagicMock:
    """
    Fake DetallePedido where:
      - .producto.ingredientes → product's full ingredient list
      - .personalizacion → list of excluded ingredient IDs (or None)
    """
    prod = _make_producto(producto_ingredientes)
    det = MagicMock()
    det.producto = prod
    det.personalizacion = personalizacion  # None or list of IDs
    return det


def _make_pedido(items: list) -> MagicMock:
    pedido = MagicMock()
    pedido.items = items
    return pedido


# ---------------------------------------------------------------------------
# The guard function we are testing
# ---------------------------------------------------------------------------


def _call_guard(pedido, session=None):
    """
    Call the availability guard directly.

    The guard is expected to be a function (or method) that accepts a Pedido-like
    object and raises BusinessRuleError if any required ingredient is unavailable.

    We import it from features.orders.service — it must be reachable and callable.
    """
    from features.orders.service import _check_ingredient_availability_guard

    _check_ingredient_availability_guard(pedido)


# ---------------------------------------------------------------------------
# Task 6.11 — single-line order requiring activo=False ingredient → blocked
# ---------------------------------------------------------------------------


class TestGuardBlocksSingleLineOrder:
    """Task 6.11: single-line order with activo=False ingredient (not excluded) → 422."""

    def test_single_line_activo_false_not_excluded_raises(self):
        """
        A single-line order whose product contains ingredient 7 (activo=False),
        and the line does NOT exclude ingredient 7 → BusinessRuleError with ingredient name.
        """
        from shared.exceptions import BusinessRuleError

        ing_unavailable = _make_ingrediente(7, "cebolla", activo=False)
        ing_ok = _make_ingrediente(3, "tomate", activo=True)
        detalle = _make_detalle(
            producto_ingredientes=[ing_ok, ing_unavailable],
            personalizacion=None,  # no exclusions
        )
        pedido = _make_pedido([detalle])

        with pytest.raises(BusinessRuleError) as exc_info:
            _call_guard(pedido)

        error_msg = str(exc_info.value).lower()
        assert "cebolla" in error_msg, (
            f"BusinessRuleError must name the unavailable ingredient. Got: {exc_info.value}"
        )

    def test_single_line_activo_false_empty_personalizacion_raises(self):
        """personalizacion=[] (empty list, not None) → still blocked."""
        from shared.exceptions import BusinessRuleError

        ing = _make_ingrediente(7, "lechuga", activo=False)
        detalle = _make_detalle(
            producto_ingredientes=[ing],
            personalizacion=[],  # empty list → no exclusions
        )
        pedido = _make_pedido([detalle])

        with pytest.raises(BusinessRuleError):
            _call_guard(pedido)

    def test_single_line_all_activo_true_passes(self):
        """All ingredients active → guard allows the advance."""
        ing1 = _make_ingrediente(1, "pan", activo=True)
        ing2 = _make_ingrediente(2, "queso", activo=True)
        detalle = _make_detalle(
            producto_ingredientes=[ing1, ing2],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle])

        # Should not raise
        _call_guard(pedido)

    def test_error_message_names_the_ingredient(self):
        """The BusinessRuleError message must contain the ingredient's nombre."""
        from shared.exceptions import BusinessRuleError

        ing = _make_ingrediente(5, "jalapeño", activo=False)
        detalle = _make_detalle(
            producto_ingredientes=[ing],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle])

        with pytest.raises(BusinessRuleError) as exc_info:
            _call_guard(pedido)

        assert "jalapeño" in str(exc_info.value), (
            "Error must name the unavailable ingredient"
        )


# ---------------------------------------------------------------------------
# Task 6.12 — activo=False ingredient excluded in ALL lines → allowed
# ---------------------------------------------------------------------------


class TestGuardAllowsWhenIngredientExcludedEverywhere:
    """Task 6.12: activo=False ingredient excluded in ALL lines that need it → advance allowed."""

    def test_single_line_excludes_unavailable_ingredient_passes(self):
        """
        A single-line order where ingredient 7 is activo=False BUT
        the line excludes ingredient 7 (personalizacion=[7]) → allowed.
        """
        ing = _make_ingrediente(7, "cebolla", activo=False)
        detalle = _make_detalle(
            producto_ingredientes=[ing],
            personalizacion=[7],  # ingredient 7 is excluded
        )
        pedido = _make_pedido([detalle])

        # Should not raise
        _call_guard(pedido)

    def test_excluded_ingredient_among_others_passes(self):
        """
        Line has multiple ingredients; only the activo=False one is excluded → allowed.
        """
        ing_ok = _make_ingrediente(3, "tomate", activo=True)
        ing_unavailable = _make_ingrediente(7, "cebolla", activo=False)
        detalle = _make_detalle(
            producto_ingredientes=[ing_ok, ing_unavailable],
            personalizacion=[7],  # exclude the unavailable one
        )
        pedido = _make_pedido([detalle])

        _call_guard(pedido)

    def test_different_excluded_id_still_blocked(self):
        """
        personalizacion excludes ingredient 99, but the activo=False ingredient is 7 → blocked.
        """
        from shared.exceptions import BusinessRuleError

        ing = _make_ingrediente(7, "ajo", activo=False)
        detalle = _make_detalle(
            producto_ingredientes=[ing],
            personalizacion=[99],  # wrong exclusion — ingredient 7 still required
        )
        pedido = _make_pedido([detalle])

        with pytest.raises(BusinessRuleError):
            _call_guard(pedido)


# ---------------------------------------------------------------------------
# Task 6.13 — two-line order: A excludes, B requires → BLOCKED (order-level)
# ---------------------------------------------------------------------------


class TestGuardTwoLineOrderOneRequires:
    """Task 6.13: line A excludes activo=False ingredient, line B requires it → blocked."""

    def test_two_lines_one_excludes_one_requires_is_blocked(self):
        """
        Order has two lines:
          - Line A: product has ingredient 7 (activo=False), line excludes it.
          - Line B: product has ingredient 7 (activo=False), line does NOT exclude it.
        → Whole order blocked (line B requires it).
        """
        from shared.exceptions import BusinessRuleError

        ing_unavailable = _make_ingrediente(7, "cebolla", activo=False)

        # Line A excludes ingredient 7
        detalle_a = _make_detalle(
            producto_ingredientes=[ing_unavailable],
            personalizacion=[7],
        )
        # Line B does not exclude ingredient 7
        detalle_b = _make_detalle(
            producto_ingredientes=[ing_unavailable],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle_a, detalle_b])

        with pytest.raises(BusinessRuleError):
            _call_guard(pedido)

    def test_two_lines_both_exclude_passes(self):
        """Both lines exclude the activo=False ingredient → allowed."""
        ing_unavailable = _make_ingrediente(7, "cebolla", activo=False)

        detalle_a = _make_detalle(
            producto_ingredientes=[ing_unavailable],
            personalizacion=[7],
        )
        detalle_b = _make_detalle(
            producto_ingredientes=[ing_unavailable],
            personalizacion=[7],
        )
        pedido = _make_pedido([detalle_a, detalle_b])

        _call_guard(pedido)  # must not raise

    def test_two_lines_different_products_one_unavailable_not_excluded(self):
        """
        Line A has a different product (no ingredient 7). Line B has ingredient 7
        (activo=False, not excluded) → blocked.
        """
        from shared.exceptions import BusinessRuleError

        ing_other = _make_ingrediente(3, "tomate", activo=True)
        ing_unavailable = _make_ingrediente(7, "cebolla", activo=False)

        detalle_a = _make_detalle(
            producto_ingredientes=[ing_other],
            personalizacion=None,
        )
        detalle_b = _make_detalle(
            producto_ingredientes=[ing_other, ing_unavailable],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle_a, detalle_b])

        with pytest.raises(BusinessRuleError):
            _call_guard(pedido)


# ---------------------------------------------------------------------------
# Task 6.14 — block lifts when activo=True; guard ignores non-kitchen transitions
# ---------------------------------------------------------------------------


class TestGuardLiftsAndNonKitchenTransitions:
    """Task 6.14: block lifts after activo=True; guard doesn't affect other transitions."""

    def test_block_lifts_when_activo_becomes_true(self):
        """Once activo=True the guard no longer blocks."""
        # Previously unavailable, now restored
        ing = _make_ingrediente(7, "cebolla", activo=True)
        detalle = _make_detalle(
            producto_ingredientes=[ing],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle])

        # Must not raise — block is lifted
        _call_guard(pedido)

    def test_guard_does_not_intervene_on_non_kitchen_transition(self):
        """
        The availability guard must only be invoked for kitchen-advancing transitions
        (CONFIRMADO→EN_PREPARACION, EN_PREPARACION→TERMINADO). For other transitions
        (e.g. cancellation) the guard is NOT called.

        This is enforced by the avanzar_estado dispatcher, not by the guard itself.
        We test that the guard function exists and is separately invocable, and that
        the dispatcher only calls it for the two kitchen transitions.
        """
        # Verify the guard function is importable and callable
        from features.orders.service import _check_ingredient_availability_guard

        assert callable(_check_ingredient_availability_guard), (
            "_check_ingredient_availability_guard must be a callable in orders/service.py"
        )

    def test_guard_handles_empty_product_ingredient_list(self):
        """Products with no ingredients → guard allows (nothing to check)."""
        detalle = _make_detalle(
            producto_ingredientes=[],
            personalizacion=None,
        )
        pedido = _make_pedido([detalle])

        _call_guard(pedido)  # must not raise

    def test_guard_handles_order_with_no_items(self):
        """Empty order (no items) → guard allows (edge case)."""
        pedido = _make_pedido([])

        _call_guard(pedido)  # must not raise


# ---------------------------------------------------------------------------
# Task 6.15 — integration: avanzar_estado invokes the guard for kitchen transitions
# ---------------------------------------------------------------------------


class TestAvanzarEstadoInvokesGuard:
    """
    Verify that avanzar_estado calls the guard for CONFIRMADO→EN_PREPARACION
    and EN_PREPARACION→TERMINADO but NOT for other transitions.
    """

    def test_avanzar_estado_calls_guard_for_confirmado_en_preparacion(self):
        """
        When nuevo_estado=EN_PREPARACION (from CONFIRMADO), avanzar_estado
        must call _check_ingredient_availability_guard.
        """
        from features.orders.service import OrderService

        # We need to patch deeply to avoid DB access:
        # - The read-only session (validate phase)
        # - _check_ingredient_availability_guard
        # - transicionar_estado (don't actually run the UoW)
        with (
            patch("features.orders.service._check_ingredient_availability_guard") as mock_guard,
            patch.object(OrderService, "transicionar_estado") as mock_trans,
            patch("shared.unit_of_work.get_session_factory") as mock_factory,
        ):
            # Build a fake session that returns a valid pedido and user
            fake_session = MagicMock()
            mock_factory.return_value.return_value = fake_session

            fake_order_repo = MagicMock()
            fake_user_repo = MagicMock()

            fake_pedido = MagicMock()
            fake_pedido.estado_codigo = "CONFIRMADO"
            fake_pedido.user_id = 1
            fake_pedido.direccion_entrega_id = None
            fake_order_repo.find_by_id.return_value = fake_pedido

            fake_user = MagicMock()
            fake_user.roles = [MagicMock(codigo="COCINA")]
            fake_user_repo.find_by_id_with_roles.return_value = fake_user

            mock_trans.return_value = fake_pedido

            with (
                patch("features.orders.service.OrderRepository", return_value=fake_order_repo),
                patch("features.orders.service.UserProfileRepository", return_value=fake_user_repo),
            ):
                svc = OrderService()
                svc.avanzar_estado(
                    user_id=1,
                    pedido_id=1,
                    nuevo_estado="EN_PREPARACION",
                )

            mock_guard.assert_called_once()

    def test_avanzar_estado_calls_guard_for_en_preparacion_terminado(self):
        """avanzar_estado must call the guard for EN_PREPARACION→TERMINADO."""
        from features.orders.service import OrderService

        with (
            patch("features.orders.service._check_ingredient_availability_guard") as mock_guard,
            patch.object(OrderService, "transicionar_estado") as mock_trans,
            patch("shared.unit_of_work.get_session_factory") as mock_factory,
        ):
            fake_session = MagicMock()
            mock_factory.return_value.return_value = fake_session

            fake_order_repo = MagicMock()
            fake_user_repo = MagicMock()

            fake_pedido = MagicMock()
            fake_pedido.estado_codigo = "EN_PREPARACION"
            fake_pedido.user_id = 1
            fake_pedido.direccion_entrega_id = None
            fake_order_repo.find_by_id.return_value = fake_pedido

            fake_user = MagicMock()
            fake_user.roles = [MagicMock(codigo="COCINA")]
            fake_user_repo.find_by_id_with_roles.return_value = fake_user

            mock_trans.return_value = fake_pedido

            with (
                patch("features.orders.service.OrderRepository", return_value=fake_order_repo),
                patch("features.orders.service.UserProfileRepository", return_value=fake_user_repo),
            ):
                svc = OrderService()
                svc.avanzar_estado(
                    user_id=1,
                    pedido_id=1,
                    nuevo_estado="TERMINADO",
                )

            mock_guard.assert_called_once()

    def test_avanzar_estado_does_not_call_guard_for_cancellation(self):
        """avanzar_estado must NOT call the guard for cancellation transitions."""
        from features.orders.service import OrderService

        with (
            patch("features.orders.service._check_ingredient_availability_guard") as mock_guard,
            patch.object(OrderService, "transicionar_estado") as mock_trans,
            patch("shared.unit_of_work.get_session_factory") as mock_factory,
        ):
            fake_session = MagicMock()
            mock_factory.return_value.return_value = fake_session

            fake_order_repo = MagicMock()
            fake_user_repo = MagicMock()

            fake_pedido = MagicMock()
            fake_pedido.estado_codigo = "EN_PREPARACION"
            fake_pedido.user_id = 1
            fake_pedido.direccion_entrega_id = None
            fake_order_repo.find_by_id.return_value = fake_pedido

            fake_user = MagicMock()
            fake_user.roles = [MagicMock(codigo="ADMIN")]
            fake_user_repo.find_by_id_with_roles.return_value = fake_user

            mock_trans.return_value = fake_pedido

            with (
                patch("features.orders.service.OrderRepository", return_value=fake_order_repo),
                patch("features.orders.service.UserProfileRepository", return_value=fake_user_repo),
            ):
                svc = OrderService()
                svc.avanzar_estado(
                    user_id=1,
                    pedido_id=1,
                    nuevo_estado="CANCELADO_ADMIN",
                    motivo="Test",
                )

            mock_guard.assert_not_called()
