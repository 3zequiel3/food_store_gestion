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
# Revision identifiers — this is the only migration (all prior schema
# was created via create_all() before Alembic was set up).
# ---------------------------------------------------------------------------

revision: str = "payment_order_state_refactor"
down_revision: Union[str, None] = None
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
    op.execute("""
        INSERT INTO order_states (codigo, descripcion, orden, es_terminal)
        VALUES ('CANCELADO_ADMIN', 'Pedido cancelado por el administrador', 6, true),
               ('CANCELADO_CLIENTE', 'Pedido cancelado por el cliente', 7, true)
        ON CONFLICT (codigo) DO NOTHING
    """)

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

    # ── Step D: Create metodo_pago_usuario table (idempotent) ─────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS metodo_pago_usuario (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mp_customer_id VARCHAR,
            mp_card_id VARCHAR,
            last_four VARCHAR(4),
            expiration_month INTEGER,
            expiration_year INTEGER,
            payment_method_id VARCHAR(50) NOT NULL REFERENCES payment_methods(codigo) ON DELETE RESTRICT,
            card_brand VARCHAR(50),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_metodo_pago_usuario_usuario_id
        ON metodo_pago_usuario (usuario_id)
    """)


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
