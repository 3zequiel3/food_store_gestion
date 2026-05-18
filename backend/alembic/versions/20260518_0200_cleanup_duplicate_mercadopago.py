"""Cleanup duplicate MERCADOPAGO payment method row.

Revision ID: 20260518_0200
Revises: 20260518_0100
Create Date: 2026-05-18 02:00:00.000000

Background
----------
Migration ``payment_order_state_refactor`` renamed payment_methods.codigo
'MERCADOPAGO' -> 'TARJETA' and cascaded the rename to orders.forma_pago_codigo
and payments.forma_pago_codigo. However, ``scripts/seed.py`` kept seeding
'MERCADOPAGO' on every boot via ``on_conflict_do_nothing``. Because the
renamed row's code was now 'TARJETA', the conflict did not trigger and a
fresh 'MERCADOPAGO' row was re-inserted alongside the legitimate 'TARJETA'.

The visible symptom is "Pago online vía MercadoPago" appearing twice in
the checkout form.

This migration is the one-time cleanup. The seed itself is updated in the
same change to insert 'TARJETA' from now on.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260518_0200'
down_revision: Union[str, None] = '20260518_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Re-cascade MERCADOPAGO -> TARJETA in case the seed bug left orphan
    rows after the original refactor, then drop the duplicate MERCADOPAGO
    catalog row.

    Idempotent: if the MERCADOPAGO row is already gone, every statement is
    a no-op. If TARJETA does not exist yet (paranoid case), nothing is
    deleted — we never want to leave dangling FKs.
    """

    # Move any orders that ended up pointing to the duplicate MERCADOPAGO
    # back to TARJETA, but only if TARJETA actually exists.
    op.execute("""
        UPDATE orders
        SET forma_pago_codigo = 'TARJETA'
        WHERE forma_pago_codigo = 'MERCADOPAGO'
          AND EXISTS (SELECT 1 FROM payment_methods WHERE codigo = 'TARJETA')
    """)

    # Same defense for payments.
    op.execute("""
        UPDATE payments
        SET forma_pago_codigo = 'TARJETA'
        WHERE forma_pago_codigo = 'MERCADOPAGO'
          AND EXISTS (SELECT 1 FROM payment_methods WHERE codigo = 'TARJETA')
    """)

    # Drop the duplicate catalog row only when TARJETA exists — otherwise
    # we would leave the system without an online payment method.
    op.execute("""
        DELETE FROM payment_methods
        WHERE codigo = 'MERCADOPAGO'
          AND EXISTS (SELECT 1 FROM payment_methods WHERE codigo = 'TARJETA')
    """)


def downgrade() -> None:
    """Re-create the MERCADOPAGO row (descriptive parity with the original seed).

    Note: this does NOT undo the FK migration to TARJETA — orders/payments
    keep pointing to TARJETA. The downgrade is here for completeness so
    Alembic chain remains reversible; in practice nothing useful comes from
    running it.
    """
    op.execute("""
        INSERT INTO payment_methods (codigo, descripcion, habilitada)
        VALUES ('MERCADOPAGO', 'Pago online vía MercadoPago', true)
        ON CONFLICT (codigo) DO NOTHING
    """)
