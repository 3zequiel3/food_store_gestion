"""create product_images table and backfill from products.imagen_url

Revision ID: 7a1b2c3d4e5f
Revises: 0b02f52c7d8a
Create Date: 2026-05-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "0b02f52c7d8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create product_images table and backfill existing imagen_url values."""
    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "es_primaria", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: for each product with imagen_url, insert a primary image row
    op.execute("""
        INSERT INTO product_images (producto_id, url, orden, es_primaria, creado_en, actualizado_en)
        SELECT id, imagen_url, 0, true, NOW(), NOW()
        FROM products
        WHERE imagen_url IS NOT NULL AND eliminado_en IS NULL
    """)


def downgrade() -> None:
    """Drop product_images table."""
    op.drop_table("product_images")
