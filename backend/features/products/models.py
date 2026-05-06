"""
Product domain models: Producto, ProductoCategoria, ProductoIngrediente.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import BaseModel, PivotBaseModel
from backend.features.catalog.models import Categoria, Ingrediente


# ---------------------------------------------------------------------------
# M:N pivot — Product ↔ Category
# ---------------------------------------------------------------------------

class ProductoCategoria(PivotBaseModel):
    """
    Many-to-many association between products and categories.

    Composite PK (product_id, category_id) — no surrogate id (ERD v5, migration 20260428_0001).
    """

    __tablename__ = "product_categories"

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProductoCategoria(product_id={self.product_id}, category_id={self.category_id})>"


# ---------------------------------------------------------------------------
# M:N pivot — Product ↔ Ingredient
# ---------------------------------------------------------------------------

class ProductoIngrediente(PivotBaseModel):
    """
    Many-to-many association between products and ingredients.

    Composite PK (product_id, ingredient_id) — no surrogate id (ERD v5, migration 20260428_0001).
    """

    __tablename__ = "product_ingredients"

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ProductoIngrediente(product_id={self.product_id}, ingredient_id={self.ingredient_id})>"
        )


# ---------------------------------------------------------------------------
# Producto
# ---------------------------------------------------------------------------

class Producto(BaseModel):
    """
    Product entity aligned with ERD v5.

    CHECK constraints:
    - precio > 0          (cannot sell a product for free or negative)
    - stock_cantidad >= 0 (stock cannot go negative at DB level)

    Both constraints are defined on the model; Alembic autogenerate may not
    detect them — they are manually verified and added in migration 0001.
    """

    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_products_precio_positivo"),
        CheckConstraint("stock_cantidad >= 0", name="ck_products_stock_no_negativo"),
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    stock_cantidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    imagen_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # M:N relationships via pivot tables
    categorias: Mapped[List[Categoria]] = relationship(
        "Categoria",
        secondary="product_categories",
        viewonly=False,
        lazy="select",
    )
    ingredientes: Mapped[List[Ingrediente]] = relationship(
        "Ingrediente",
        secondary="product_ingredients",
        viewonly=False,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Producto(id={self.id}, nombre={self.nombre!r}, precio={self.precio})>"
