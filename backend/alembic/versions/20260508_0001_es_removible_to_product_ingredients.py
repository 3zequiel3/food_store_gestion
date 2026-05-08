"""add es_removible to product_ingredients

Revision ID: es_removible_product_ingredients
Revises: 77bcb99d97db
Create Date: 2026-05-08 00:01:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "es_removible_product_ingredients"
down_revision: Union[str, None] = "77bcb99d97db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add es_removible column to product_ingredients table.

    Column is NOT NULL with server_default=false so the migration is safe
    even if the table already has rows in any environment.
    """
    op.add_column(
        "product_ingredients",
        sa.Column(
            "es_removible",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove es_removible column from product_ingredients."""
    op.drop_column("product_ingredients", "es_removible")
