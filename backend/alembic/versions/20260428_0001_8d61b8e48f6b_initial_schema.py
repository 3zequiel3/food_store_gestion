"""Initial schema — all 16 tables for Food Store.

Revision ID: 8d61b8e48f6b
Revises:
Create Date: 2026-04-28 00:00:00.000000

This migration creates the complete initial database schema aligned with ERD v5.

Tables created (in dependency order):
  1. roles
  2. payment_methods
  3. order_states
  4. users
  5. user_roles
  6. refresh_tokens
  7. delivery_addresses
  8. categories
  9. ingredients
  10. products
  11. product_categories
  12. product_ingredients
  13. orders
  14. order_items
  15. payments
  16. order_state_history

Notes:
- ARRAY(Integer) for order_items.personalizacion added manually (autogenerate does not detect it).
- CHECK constraints added manually (autogenerate does not detect SQLAlchemy CheckConstraint on ARRAY/Numeric).
- Naming convention follows the project MetaData convention:
    ix_<col_label>, uq_<table>_<col>, ck_<table>_<name>, fk_<table>_<col>_<referred>, pk_<table>
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d61b8e48f6b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. roles — catalog with stable integer IDs (1=ADMIN..4=CLIENT)
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("codigo", name=op.f("uq_roles_codigo")),
    )

    # ------------------------------------------------------------------
    # 2. payment_methods — VARCHAR semantic PK via unique codigo
    # ------------------------------------------------------------------
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("habilitada", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_methods")),
        sa.UniqueConstraint("codigo", name=op.f("uq_payment_methods_codigo")),
    )

    # ------------------------------------------------------------------
    # 3. order_states — catalog with ordering and terminal flag
    # ------------------------------------------------------------------
    op.create_table(
        "order_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("es_terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_states")),
        sa.UniqueConstraint("codigo", name=op.f("uq_order_states_codigo")),
    )

    # ------------------------------------------------------------------
    # 4. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("apellido", sa.String(length=100), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # 5. user_roles — M:N pivot
    # ------------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name=op.f("fk_user_roles_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_user_roles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )

    # ------------------------------------------------------------------
    # 6. refresh_tokens
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)

    # ------------------------------------------------------------------
    # 7. delivery_addresses
    # ------------------------------------------------------------------
    op.create_table(
        "delivery_addresses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("calle", sa.String(length=255), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("ciudad", sa.String(length=100), nullable=False),
        sa.Column("codigo_postal", sa.String(length=20), nullable=False),
        sa.Column("referencia", sa.String(length=500), nullable=True),
        sa.Column("es_principal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_delivery_addresses_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_addresses")),
    )
    op.create_index(op.f("ix_delivery_addresses_user_id"), "delivery_addresses", ["user_id"], unique=False)

    # ------------------------------------------------------------------
    # 8. categories — self-referential tree
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("padre_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["padre_id"], ["categories.id"],
            name=op.f("fk_categories_padre_id_categories"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )

    # ------------------------------------------------------------------
    # 9. ingredients
    # ------------------------------------------------------------------
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("es_alergeno", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredients")),
        sa.UniqueConstraint("nombre", name=op.f("uq_ingredients_nombre")),
    )

    # ------------------------------------------------------------------
    # 10. products — with CHECK constraints on precio and stock
    # ------------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock_cantidad", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("imagen_url", sa.String(length=500), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("precio > 0", name="ck_products_precio_positivo"),
        sa.CheckConstraint("stock_cantidad >= 0", name="ck_products_stock_no_negativo"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_nombre"), "products", ["nombre"], unique=False)
    op.create_index(op.f("ix_products_disponible"), "products", ["disponible"], unique=False)

    # ------------------------------------------------------------------
    # 11. product_categories — M:N pivot
    # ------------------------------------------------------------------
    op.create_table(
        "product_categories",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"],
            name=op.f("fk_product_categories_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name=op.f("fk_product_categories_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", "category_id", name=op.f("pk_product_categories")),
    )

    # ------------------------------------------------------------------
    # 12. product_ingredients — M:N pivot
    # ------------------------------------------------------------------
    op.create_table(
        "product_ingredients",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"],
            name=op.f("fk_product_ingredients_ingredient_id_ingredients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name=op.f("fk_product_ingredients_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", "ingredient_id", name=op.f("pk_product_ingredients")),
    )

    # ------------------------------------------------------------------
    # 13. orders
    # ------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("direccion_entrega_id", sa.Integer(), nullable=False),
        sa.Column("direccion_snapshot", sa.String(length=500), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "costo_envio",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("forma_pago_codigo", sa.String(length=50), nullable=False),
        sa.Column(
            "estado_codigo",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["direccion_entrega_id"], ["delivery_addresses.id"],
            name=op.f("fk_orders_direccion_entrega_id_delivery_addresses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["estado_codigo"], ["order_states.codigo"],
            name=op.f("fk_orders_estado_codigo_order_states"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["forma_pago_codigo"], ["payment_methods.codigo"],
            name=op.f("fk_orders_forma_pago_codigo_payment_methods"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_orders_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_index(op.f("ix_orders_estado_codigo"), "orders", ["estado_codigo"], unique=False)

    # ------------------------------------------------------------------
    # 14. order_items — with ARRAY(Integer) for personalizacion and CHECK cantidad > 0
    # ------------------------------------------------------------------
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("nombre_snapshot", sa.String(length=255), nullable=False),
        sa.Column("precio_snapshot", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        # ARRAY(Integer) manually added — autogenerate does not detect PG-specific types
        sa.Column("personalizacion", ARRAY(sa.Integer()), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("cantidad > 0", name="ck_order_items_cantidad_positiva"),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["orders.id"],
            name=op.f("fk_order_items_pedido_id_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"], ["products.id"],
            name=op.f("fk_order_items_producto_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_pedido_id"), "order_items", ["pedido_id"], unique=False)

    # ------------------------------------------------------------------
    # 15. payments — NO unique on pedido_id (RN-PA08)
    # ------------------------------------------------------------------
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("forma_pago_codigo", sa.String(length=50), nullable=False),
        sa.Column("mp_payment_id", sa.String(length=255), nullable=True),
        sa.Column("mp_status", sa.String(length=50), nullable=True),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["forma_pago_codigo"], ["payment_methods.codigo"],
            name=op.f("fk_payments_forma_pago_codigo_payment_methods"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["orders.id"],
            name=op.f("fk_payments_pedido_id_orders"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_payments_idempotency_key")),
    )
    op.create_index(op.f("ix_payments_pedido_id"), "payments", ["pedido_id"], unique=False)

    # ------------------------------------------------------------------
    # 16. order_state_history — append-only, no actualizado_en, no eliminado_en
    # ------------------------------------------------------------------
    op.create_table(
        "order_state_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("estado_anterior_codigo", sa.String(length=50), nullable=True),
        sa.Column("estado_nuevo_codigo", sa.String(length=50), nullable=False),
        sa.Column("cambiado_por_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cambiado_por_id"], ["users.id"],
            name=op.f("fk_order_state_history_cambiado_por_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["estado_anterior_codigo"], ["order_states.codigo"],
            name=op.f("fk_order_state_history_estado_anterior_codigo_order_states"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["estado_nuevo_codigo"], ["order_states.codigo"],
            name=op.f("fk_order_state_history_estado_nuevo_codigo_order_states"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["orders.id"],
            name=op.f("fk_order_state_history_pedido_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_state_history")),
    )
    op.create_index(
        op.f("ix_order_state_history_pedido_id"),
        "order_state_history",
        ["pedido_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(op.f("ix_order_state_history_pedido_id"), table_name="order_state_history")
    op.drop_table("order_state_history")

    op.drop_index(op.f("ix_payments_pedido_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_order_items_pedido_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_estado_codigo"), table_name="orders")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_table("product_ingredients")
    op.drop_table("product_categories")

    op.drop_index(op.f("ix_products_disponible"), table_name="products")
    op.drop_index(op.f("ix_products_nombre"), table_name="products")
    op.drop_table("products")

    op.drop_table("ingredients")
    op.drop_table("categories")

    op.drop_index(op.f("ix_delivery_addresses_user_id"), table_name="delivery_addresses")
    op.drop_table("delivery_addresses")

    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("order_states")
    op.drop_table("payment_methods")
    op.drop_table("roles")
