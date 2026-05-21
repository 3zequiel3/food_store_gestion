"""Re-introduce EN_CAMINO state into order_states catalog

Revision ID: 20260521_0100
Revises: 20260518_0200
Create Date: 2026-05-21 01:00:00.000000

Reverses part of 20260518_0100 (rename_en_camino_to_terminado) by
re-inserting EN_CAMINO as a distinct state between TERMINADO and ENTREGADO.

Also shifts the `orden` of all states >= 5 up by 1 so EN_CAMINO fits at 5.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260521_0100'
down_revision: Union[str, None] = '20260518_0200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert EN_CAMINO into order_states and shift orden for states >= 5."""

    # Shift existing states with orden >= 5 up by 1 to make room for EN_CAMINO at 5.
    op.execute("""
        UPDATE order_states
        SET orden = orden + 1
        WHERE orden >= 5
    """)

    # Insert EN_CAMINO at orden=5 (between TERMINADO=4 and ENTREGADO=6).
    # Idempotent: ON CONFLICT on codigo ensures re-runs are safe.
    op.execute("""
        INSERT INTO order_states (codigo, descripcion, orden, es_terminal)
        VALUES ('EN_CAMINO', 'Pedido en camino al cliente', 5, false)
        ON CONFLICT (codigo) DO NOTHING
    """)


def downgrade() -> None:
    """Remove EN_CAMINO and shift orden back down.

    Safe downgrade: refuses to proceed if any orders are still in EN_CAMINO
    state, to avoid orphaning FK references.
    """

    # Guard: cannot downgrade if orders are in EN_CAMINO state.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM orders WHERE estado_codigo = 'EN_CAMINO') THEN
                RAISE EXCEPTION 'Cannot downgrade: orders exist in EN_CAMINO state. Transition them first.';
            END IF;
        END $$;
    """)

    # Remove EN_CAMINO from catalog.
    op.execute("DELETE FROM order_states WHERE codigo = 'EN_CAMINO'")

    # Shift orden back down for states that were bumped (now orden > 5).
    op.execute("""
        UPDATE order_states
        SET orden = orden - 1
        WHERE orden > 5
    """)
