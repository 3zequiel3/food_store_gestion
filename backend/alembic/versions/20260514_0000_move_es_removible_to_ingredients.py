"""move es_removible from product_ingredients to ingredients

Revision ID: move_es_removible_to_ingredients
Revises: 7a1b2c3d4e5f
Create Date: 2026-05-14 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "move_es_removible_to_ingredients"
down_revision: Union[str, None] = "7a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move es_removible column from product_ingredients to ingredients.

    1. Add es_removible to ingredients (NOT NULL with server_default=false).
    2. Drop es_removible from product_ingredients.

    No data backfill needed — existing pivot values are mostly false (default)
    and the flag is now a global property of the ingredient.
    """
    op.add_column(
        "ingredients",
        sa.Column(
            "es_removible",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.drop_column("product_ingredients", "es_removible")


def downgrade() -> None:
    """Restore es_removible on product_ingredients, remove from ingredients."""
    op.add_column(
        "product_ingredients",
        sa.Column(
            "es_removible",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.drop_column("ingredients", "es_removible")
