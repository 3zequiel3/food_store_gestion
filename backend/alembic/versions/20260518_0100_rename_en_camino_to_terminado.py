"""Rename EN_CAMINO to TERMINADO

Revision ID: 20260518_0100
Revises: add_es_removible_to_ingredients
Create Date: 2026-05-18 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260518_0100'
down_revision: Union[str, None] = 'add_es_removible_to_ingredients'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename EN_CAMINO to TERMINADO in all tables.

    Idempotent: a re-run with no remaining EN_CAMINO rows is a no-op.
    """

    # Update order_states catalog table (parent of the FK).
    op.execute("""
        UPDATE order_states
        SET codigo = 'TERMINADO',
            descripcion = 'Pedido listo para ser retirado o entregado'
        WHERE codigo = 'EN_CAMINO'
    """)

    # Update orders.estado_codigo (cascades semantically with the catalog rename).
    op.execute("""
        UPDATE orders
        SET estado_codigo = 'TERMINADO'
        WHERE estado_codigo = 'EN_CAMINO'
    """)

    # Update order_state_history rows whose "from" code was EN_CAMINO.
    op.execute("""
        UPDATE order_state_history
        SET estado_anterior_codigo = 'TERMINADO'
        WHERE estado_anterior_codigo = 'EN_CAMINO'
    """)

    # Update order_state_history rows whose "to" code was EN_CAMINO.
    op.execute("""
        UPDATE order_state_history
        SET estado_nuevo_codigo = 'TERMINADO'
        WHERE estado_nuevo_codigo = 'EN_CAMINO'
    """)


def downgrade() -> None:
    """Revert TERMINADO back to EN_CAMINO."""

    op.execute("""
        UPDATE order_state_history
        SET estado_nuevo_codigo = 'EN_CAMINO'
        WHERE estado_nuevo_codigo = 'TERMINADO'
    """)

    op.execute("""
        UPDATE order_state_history
        SET estado_anterior_codigo = 'EN_CAMINO'
        WHERE estado_anterior_codigo = 'TERMINADO'
    """)

    op.execute("""
        UPDATE orders
        SET estado_codigo = 'EN_CAMINO'
        WHERE estado_codigo = 'TERMINADO'
    """)

    op.execute("""
        UPDATE order_states
        SET codigo = 'EN_CAMINO',
            descripcion = 'Pedido en camino al cliente'
        WHERE codigo = 'TERMINADO'
    """)
