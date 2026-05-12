"""add motivo to order_state_history

Revision ID: 0b02f52c7d8a
Revises: 512cfb7c337d
Create Date: 2026-05-12 13:08:33.335362

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0b02f52c7d8a'
down_revision: Union[str, Sequence[str], None] = '512cfb7c337d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable motivo column to order_state_history."""
    op.add_column('order_state_history', sa.Column('motivo', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove motivo column from order_state_history."""
    op.drop_column('order_state_history', 'motivo')
