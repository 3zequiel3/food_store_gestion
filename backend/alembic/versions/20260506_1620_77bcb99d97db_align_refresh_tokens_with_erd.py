"""align refresh_tokens with erd

Revision ID: 77bcb99d97db
Revises: 8d61b8e48f6b
Create Date: 2026-05-06 16:20:06.518535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77bcb99d97db'
down_revision: Union[str, Sequence[str], None] = '8d61b8e48f6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: token_hash String(255) -> String(64) to match ERD v5 §3.1 CHAR(64)."""
    op.alter_column(
        "refresh_tokens",
        "token_hash",
        existing_type=sa.String(length=255),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema: token_hash String(64) -> String(255)."""
    op.alter_column(
        "refresh_tokens",
        "token_hash",
        existing_type=sa.String(length=64),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
