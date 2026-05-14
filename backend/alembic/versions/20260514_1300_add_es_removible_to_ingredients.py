"""add missing es_removible column to ingredients table.

This migration was accidentally omitted when consolidating to a single
migration file. The previous migration (payment_order_state_refactor)
was marked as executed in alembic_version but never created this column.

"""

from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_es_removible_to_ingredients"
down_revision: Union[str, None] = "payment_order_state_refactor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS es_removible BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute("ALTER TABLE product_ingredients DROP COLUMN IF EXISTS es_removible")


def downgrade() -> None:
    op.execute("ALTER TABLE ingredients DROP COLUMN IF EXISTS es_removible")
    op.execute(
        "ALTER TABLE product_ingredients ADD COLUMN IF NOT EXISTS es_removible BOOLEAN NOT NULL DEFAULT false"
    )
