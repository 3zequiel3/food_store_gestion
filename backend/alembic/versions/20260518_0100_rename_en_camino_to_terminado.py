"""Rename EN_CAMINO to TERMINADO

Revision ID: 20260518_0100
Revises: 20260514_1300
Create Date: 2026-05-18 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260518_0100'
down_revision: Union[str, None] = '20260514_1300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename EN_CAMINO to TERMINADO in all tables."""
    
    # Update estados_pedido table
    op.execute("""
        UPDATE estados_pedido 
        SET codigo = 'TERMINADO', 
            descripcion = 'Pedido listo para ser retirado o entregado'
        WHERE codigo = 'EN_CAMINO'
    """)
    
    # Update orders table
    op.execute("""
        UPDATE orders 
        SET estado_codigo = 'TERMINADO'
        WHERE estado_codigo = 'EN_CAMINO'
    """)
    
    # Update order_state_history table - estado_anterior_codigo
    op.execute("""
        UPDATE order_state_history 
        SET estado_anterior_codigo = 'TERMINADO'
        WHERE estado_anterior_codigo = 'EN_CAMINO'
    """)
    
    # Update order_state_history table - estado_nuevo_codigo
    op.execute("""
        UPDATE order_state_history 
        SET estado_nuevo_codigo = 'TERMINADO'
        WHERE estado_nuevo_codigo = 'EN_CAMINO'
    """)


def downgrade() -> None:
    """Revert TERMINADO back to EN_CAMINO."""
    
    # Update order_state_history table - estado_nuevo_codigo
    op.execute("""
        UPDATE order_state_history 
        SET estado_nuevo_codigo = 'EN_CAMINO'
        WHERE estado_nuevo_codigo = 'TERMINADO'
    """)
    
    # Update order_state_history table - estado_anterior_codigo
    op.execute("""
        UPDATE order_state_history 
        SET estado_anterior_codigo = 'EN_CAMINO'
        WHERE estado_anterior_codigo = 'TERMINADO'
    """)
    
    # Update orders table
    op.execute("""
        UPDATE orders 
        SET estado_codigo = 'EN_CAMINO'
        WHERE estado_codigo = 'TERMINADO'
    """)
    
    # Update estados_pedido table
    op.execute("""
        UPDATE estados_pedido 
        SET codigo = 'EN_CAMINO',
            descripcion = 'Pedido en camino al cliente'
        WHERE codigo = 'TERMINADO'
    """)
