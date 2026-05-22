"""
Unit tests — Task 5.1: kitchen payload includes full ingredient list and resolves
exclusion IDs to names (P1.4 backend).

Design D10: the kitchen payload builder joins product_ingredients → ingredients
to attach {id, nombre, es_removible} for each product line, and resolves the
personalizacion exclusion IDs to names so the cook sees ingredient names, not IDs.

These tests drive the schema changes (CocinaPedidoItem adds ingredientes and
exclusiones_nombres) and the service-layer join.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — build fake ORM objects for unit tests (no DB needed)
# ---------------------------------------------------------------------------


def _make_ingrediente(id_: int, nombre: str, es_removible: bool = False) -> MagicMock:
    ing = MagicMock()
    ing.id = id_
    ing.nombre = nombre
    ing.es_removible = es_removible
    return ing


def _make_item(
    producto_id: int,
    nombre_snapshot: str,
    cantidad: int = 1,
    personalizacion: list[int] | None = None,
    ingredientes: list | None = None,
) -> MagicMock:
    """Build a fake DetallePedido with a lazy-loaded product and its ingredients."""
    item = MagicMock()
    item.producto_id = producto_id
    item.nombre_snapshot = nombre_snapshot
    item.cantidad = cantidad
    item.personalizacion = personalizacion or []

    # item.producto → Producto with .ingredientes list
    producto = MagicMock()
    producto.ingredientes = ingredientes or []
    item.producto = producto
    return item


# ---------------------------------------------------------------------------
# Task 5.1 — CocinaPedidoItem schema must carry ingredientes and exclusiones_nombres
# ---------------------------------------------------------------------------


class TestCocinaPedidoItemSchema:
    """
    CocinaPedidoItem must have two new fields:
      - ingredientes: list of {id, nombre, es_removible}
      - exclusiones_nombres: list of names resolved from personalizacion IDs
    """

    def test_schema_has_ingredientes_field(self):
        """CocinaPedidoItem.model_fields must contain 'ingredientes'."""
        from features.cocina.schemas import CocinaPedidoItem

        assert "ingredientes" in CocinaPedidoItem.model_fields, (
            "CocinaPedidoItem must define an 'ingredientes' field"
        )

    def test_schema_has_exclusiones_nombres_field(self):
        """CocinaPedidoItem.model_fields must contain 'exclusiones_nombres'."""
        from features.cocina.schemas import CocinaPedidoItem

        assert "exclusiones_nombres" in CocinaPedidoItem.model_fields, (
            "CocinaPedidoItem must define an 'exclusiones_nombres' field"
        )

    def test_ingrediente_info_schema_has_required_fields(self):
        """
        The ingredient info nested object must expose id, nombre, es_removible.
        """
        from features.cocina.schemas import IngredienteInfo

        for field in ("id", "nombre", "es_removible"):
            assert field in IngredienteInfo.model_fields, (
                f"IngredienteInfo must have '{field}' field"
            )

    def test_ingredientes_defaults_to_empty_list(self):
        """ingredientes is optional — defaults to an empty list."""
        from features.cocina.schemas import CocinaPedidoItem

        item = CocinaPedidoItem(
            producto_id=1,
            nombre_snapshot="Burger",
            cantidad=1,
        )
        assert item.ingredientes == []

    def test_exclusiones_nombres_defaults_to_empty_list(self):
        """exclusiones_nombres is optional — defaults to an empty list."""
        from features.cocina.schemas import CocinaPedidoItem

        item = CocinaPedidoItem(
            producto_id=1,
            nombre_snapshot="Burger",
            cantidad=1,
        )
        assert item.exclusiones_nombres == []


# ---------------------------------------------------------------------------
# Task 5.1 — kitchen service builds the payload with ingredient names
# ---------------------------------------------------------------------------


class TestKitchenPayloadIngredients:
    """
    get_kitchen_orders() must populate ingredientes from the product relationship
    and resolve personalizacion IDs to exclusiones_nombres.
    """

    def test_payload_includes_full_ingredient_list(self):
        """
        Given a product with three ingredients, the payload item carries all three
        with nombre and es_removible.
        """
        ing1 = _make_ingrediente(1, "Lechuga", es_removible=True)
        ing2 = _make_ingrediente(2, "Tomate", es_removible=True)
        ing3 = _make_ingrediente(3, "Carne", es_removible=False)

        item = _make_item(
            producto_id=10,
            nombre_snapshot="Burger",
            cantidad=2,
            personalizacion=[],
            ingredientes=[ing1, ing2, ing3],
        )

        result = _build_item_payload(item)

        assert len(result.ingredientes) == 3
        nombres = {i.nombre for i in result.ingredientes}
        assert nombres == {"Lechuga", "Tomate", "Carne"}

    def test_payload_resolves_exclusion_ids_to_names(self):
        """
        When personalizacion=[1, 3], exclusiones_nombres must be ['Lechuga', 'Carne']
        (resolved from the ingredient list, maintaining determinism).
        """
        ing1 = _make_ingrediente(1, "Lechuga", es_removible=True)
        ing2 = _make_ingrediente(2, "Tomate", es_removible=True)
        ing3 = _make_ingrediente(3, "Carne", es_removible=False)

        item = _make_item(
            producto_id=10,
            nombre_snapshot="Burger",
            cantidad=1,
            personalizacion=[1, 3],
            ingredientes=[ing1, ing2, ing3],
        )

        result = _build_item_payload(item)

        assert set(result.exclusiones_nombres) == {"Lechuga", "Carne"}

    def test_payload_exclusiones_nombres_empty_when_no_personalizacion(self):
        """When personalizacion is empty, exclusiones_nombres must be []."""
        ing = _make_ingrediente(1, "Lechuga", es_removible=True)

        item = _make_item(
            producto_id=5,
            nombre_snapshot="Salad",
            cantidad=1,
            personalizacion=[],
            ingredientes=[ing],
        )

        result = _build_item_payload(item)

        assert result.exclusiones_nombres == []

    def test_payload_exclusiones_unknown_id_is_ignored(self):
        """
        An exclusion ID that does not match any ingredient of the product is
        silently ignored (defensive — should not happen in valid data).
        """
        ing = _make_ingrediente(1, "Lechuga", es_removible=True)

        item = _make_item(
            producto_id=5,
            nombre_snapshot="Salad",
            cantidad=1,
            personalizacion=[99],  # 99 does not exist in this product
            ingredientes=[ing],
        )

        result = _build_item_payload(item)

        assert result.exclusiones_nombres == []

    def test_payload_product_with_no_ingredients_returns_empty_lists(self):
        """A product with no ingredients produces empty ingredientes and exclusiones."""
        item = _make_item(
            producto_id=7,
            nombre_snapshot="Water",
            cantidad=1,
            personalizacion=[],
            ingredientes=[],
        )

        result = _build_item_payload(item)

        assert result.ingredientes == []
        assert result.exclusiones_nombres == []


# ---------------------------------------------------------------------------
# Helper — call the item payload builder in isolation
# ---------------------------------------------------------------------------


def _build_item_payload(item):
    """
    Call the kitchen service item builder on a fake DetallePedido.
    Imports from features.cocina.service to keep test coupling explicit.
    """
    from features.cocina.service import _build_cocina_item

    return _build_cocina_item(item)
