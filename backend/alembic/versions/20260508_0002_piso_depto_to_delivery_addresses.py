"""add piso_depto to delivery_addresses

Revision ID: piso_depto_delivery_addresses
Revises: es_removible_product_ingredients
Create Date: 2026-05-08 00:02:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "piso_depto_delivery_addresses"
down_revision: Union[str, None] = "es_removible_product_ingredients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add piso_depto column to delivery_addresses (nullable, no default)."""
    op.add_column(
        "delivery_addresses",
        sa.Column("piso_depto", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Remove piso_depto column from delivery_addresses."""
    op.drop_column("delivery_addresses", "piso_depto")
