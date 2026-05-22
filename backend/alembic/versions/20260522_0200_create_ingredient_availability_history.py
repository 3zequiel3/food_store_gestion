"""Create ingredient_availability_history table

Revision ID: 20260522_0200
Revises: 20260522_0100
Create Date: 2026-05-22 02:00:00.000000

Creates the HistorialDisponibilidadIngrediente table (D6, Phase 6).

The previously-planned kitchen_admin_messages table is NOT created here —
it was superseded by this table (see design.md D6: "one append-on-report /
close-on-resolve log is the single source of truth").

downgrade() drops the table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260522_0200'
down_revision: Union[str, None] = '20260522_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingredient_availability_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ingrediente_id', sa.Integer(), nullable=False),
        sa.Column('reportado_por', sa.Integer(), nullable=False),
        sa.Column('pedido_id', sa.Integer(), nullable=False),
        sa.Column(
            'creado_en',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'actualizado_en',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('eliminado_en', sa.DateTime(timezone=True), nullable=True),
        # Nullable — NULL means the report is still pending.
        sa.Column('resuelto_en', sa.DateTime(timezone=True), nullable=True),
        # Nullable — set to the admin user id when resolved.
        sa.Column('resuelto_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['ingrediente_id'], ['ingredients.id'], ondelete='RESTRICT'
        ),
        sa.ForeignKeyConstraint(
            ['reportado_por'], ['users.id'], ondelete='RESTRICT'
        ),
        sa.ForeignKeyConstraint(
            ['pedido_id'], ['orders.id'], ondelete='RESTRICT'
        ),
        sa.ForeignKeyConstraint(
            ['resuelto_por'], ['users.id'], ondelete='SET NULL'
        ),
    )
    op.create_index(
        'ix_ingredient_availability_history_ingrediente_id',
        'ingredient_availability_history',
        ['ingrediente_id'],
    )
    op.create_index(
        'ix_ingredient_availability_history_pedido_id',
        'ingredient_availability_history',
        ['pedido_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_ingredient_availability_history_pedido_id',
        table_name='ingredient_availability_history',
    )
    op.drop_index(
        'ix_ingredient_availability_history_ingrediente_id',
        table_name='ingredient_availability_history',
    )
    op.drop_table('ingredient_availability_history')
