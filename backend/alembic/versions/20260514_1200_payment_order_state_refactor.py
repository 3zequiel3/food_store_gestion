"""payment/order state refactor: MERCADOPAGO→TARJETA, new cancel states, migrar CANCELADO, saved cards table.

Upgrades:
  A. Rename MERCADOPAGO → TARJETA in payment_methods, cascade to orders/payments.
  B. Add CANCELADO_ADMIN and CANCELADO_CLIENTE to order_states.
  C. Migrate existing CANCELADO orders → CANCELADO_ADMIN (catalog entry preserved).
  D. Create metodo_pago_usuario table for saved cards (CRUD deferred).
"""

from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "payment_order_state_refactor"
down_revision: Union[str, None] = "move_es_removible_to_ingredients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── Step A: Rename MERCADOPAGO → TARJETA ──────────────────────────────
    op.execute(
        "UPDATE payment_methods SET codigo = 'TARJETA' WHERE codigo = 'MERCADOPAGO'"
    )
    op.execute(
        "UPDATE orders SET forma_pago_codigo = 'TARJETA' WHERE forma_pago_codigo = 'MERCADOPAGO'"
    )
    op.execute(
        "UPDATE payments SET forma_pago_codigo = 'TARJETA' WHERE forma_pago_codigo = 'MERCADOPAGO'"
    )

    # ── Step B: Add CANCELADO_ADMIN and CANCELADO_CLIENTE to order_states ──
    op.bulk_insert(
        sa.table(
            "order_states",
            sa.column("codigo", sa.String),
            sa.column("descripcion", sa.String),
            sa.column("orden", sa.Integer),
            sa.column("es_terminal", sa.Boolean),
        ),
        [
            {
                "codigo": "CANCELADO_ADMIN",
                "descripcion": "Pedido cancelado por el administrador",
                "orden": 6,
                "es_terminal": True,
            },
            {
                "codigo": "CANCELADO_CLIENTE",
                "descripcion": "Pedido cancelado por el cliente",
                "orden": 7,
                "es_terminal": True,
            },
        ],
    )

    # ── Step C: Migrate existing CANCELADO → CANCELADO_ADMIN ──────────────
    op.execute(
        "UPDATE orders SET estado_codigo = 'CANCELADO_ADMIN' WHERE estado_codigo = 'CANCELADO'"
    )
    op.execute(
        "UPDATE order_state_history SET estado_nuevo_codigo = 'CANCELADO_ADMIN' WHERE estado_nuevo_codigo = 'CANCELADO'"
    )
    # Also update estado_anterior_codigo if any transition had CANCELADO as prior state
    op.execute(
        "UPDATE order_state_history SET estado_anterior_codigo = 'CANCELADO_ADMIN' WHERE estado_anterior_codigo = 'CANCELADO'"
    )

    # ── Step D: Create metodo_pago_usuario table ──────────────────────────
    op.create_table(
        "metodo_pago_usuario",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "usuario_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("mp_customer_id", sa.String, nullable=True),
        sa.Column("mp_card_id", sa.String, nullable=True),
        sa.Column("last_four", sa.String(4), nullable=True),
        sa.Column("expiration_month", sa.Integer, nullable=True),
        sa.Column("expiration_year", sa.Integer, nullable=True),
        sa.Column(
            "payment_method_id",
            sa.String(50),
            sa.ForeignKey("payment_methods.codigo", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("card_brand", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_metodo_pago_usuario_usuario_id",
        "metodo_pago_usuario",
        ["usuario_id"],
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # ── Reverse Step D: Drop metodo_pago_usuario ──────────────────────────
    op.drop_table("metodo_pago_usuario")

    # ── Reverse Step C: CANCELADO_ADMIN → CANCELADO ───────────────────────
    op.execute(
        "UPDATE orders SET estado_codigo = 'CANCELADO' WHERE estado_codigo = 'CANCELADO_ADMIN'"
    )
    op.execute(
        "UPDATE order_state_history SET estado_nuevo_codigo = 'CANCELADO' WHERE estado_nuevo_codigo = 'CANCELADO_ADMIN'"
    )
    op.execute(
        "UPDATE order_state_history SET estado_anterior_codigo = 'CANCELADO' WHERE estado_anterior_codigo = 'CANCELADO_ADMIN'"
    )

    # ── Reverse Step B: Remove CANCELADO_ADMIN and CANCELADO_CLIENTE ──────
    op.execute(
        "DELETE FROM order_states WHERE codigo IN ('CANCELADO_ADMIN', 'CANCELADO_CLIENTE')"
    )

    # ── Reverse Step A: TARJETA → MERCADOPAGO ─────────────────────────────
    op.execute(
        "UPDATE payment_methods SET codigo = 'MERCADOPAGO' WHERE codigo = 'TARJETA'"
    )
    op.execute(
        "UPDATE orders SET forma_pago_codigo = 'MERCADOPAGO' WHERE forma_pago_codigo = 'TARJETA'"
    )
    op.execute(
        "UPDATE payments SET forma_pago_codigo = 'MERCADOPAGO' WHERE forma_pago_codigo = 'TARJETA'"
    )
