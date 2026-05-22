"""Add activo boolean column to ingredients table

Revision ID: 20260522_0100
Revises: 20260521_0100
Create Date: 2026-05-22 01:00:00.000000

Adds Ingrediente.activo (D6, Phase 6 — ingredient kitchen availability).

- activo BOOLEAN NOT NULL DEFAULT true
- Existing rows receive activo=true via the server default (backfill included).
- downgrade() drops the column.

Distinct from es_removible (client customization) — see design.md D6.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260522_0100'
down_revision: Union[str, None] = '20260521_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add activo column with server default so all existing rows get true.
    op.add_column(
        'ingredients',
        sa.Column(
            'activo',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade() -> None:
    op.drop_column('ingredients', 'activo')
