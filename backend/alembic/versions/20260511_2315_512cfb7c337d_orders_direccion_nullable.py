"""orders_direccion_nullable

Revision ID: 512cfb7c337d
Revises: piso_depto_delivery_addresses
Create Date: 2026-05-11 23:15:44.212753

D1 — Alinear orders.direccion_entrega_id y orders.direccion_snapshot a la spec §3.3.
Habilita retiro en local (NULL = retiro en local, válido según RN-PE01).
ON DELETE SET NULL conserva el snapshot histórico aunque el cliente borre la dirección (RN-DA06).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '512cfb7c337d'
down_revision: Union[str, Sequence[str], None] = 'piso_depto_delivery_addresses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make orders.direccion_entrega_id and orders.direccion_snapshot nullable.

    Steps:
    1. Drop the existing FK on direccion_entrega_id (created with ondelete=RESTRICT).
    2. Alter direccion_entrega_id: NOT NULL → NULL.
    3. Re-create FK with ondelete=SET NULL.
    4. Alter direccion_snapshot: NOT NULL → NULL.
    """
    # Get the current connection to detect dialect (skip FK ops on SQLite)
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name != "sqlite":
        # 1. Drop the existing FK constraint using the actual PG name
        #    (discovered via pg_constraint query: fk_orders_direccion_entrega_id_delivery_addresses)
        with op.batch_alter_table("orders") as batch_op:
            # Drop the existing RESTRICT FK and recreate as SET NULL
            batch_op.drop_constraint(
                "fk_orders_direccion_entrega_id_delivery_addresses",
                type_="foreignkey",
            )
            batch_op.alter_column(
                "direccion_entrega_id",
                existing_type=sa.BigInteger(),
                nullable=True,
            )
            batch_op.create_foreign_key(
                "fk_orders_direccion_entrega_id_delivery_addresses",
                "delivery_addresses",
                ["direccion_entrega_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.alter_column(
                "direccion_snapshot",
                existing_type=sa.String(500),
                nullable=True,
            )
    else:
        # SQLite: batch_alter_table handles column alteration without FK support.
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "direccion_entrega_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
            batch_op.alter_column(
                "direccion_snapshot",
                existing_type=sa.String(500),
                nullable=True,
            )


def downgrade() -> None:
    """
    Revert orders.direccion_entrega_id and orders.direccion_snapshot to NOT NULL.

    WARNING: assumes no rows have NULL values in these columns.
    Safe in development (no production data in orders).
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name != "sqlite":
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "direccion_snapshot",
                existing_type=sa.String(500),
                nullable=False,
            )
            batch_op.drop_constraint(
                "fk_orders_direccion_entrega_id_delivery_addresses",
                type_="foreignkey",
            )
            batch_op.alter_column(
                "direccion_entrega_id",
                existing_type=sa.BigInteger(),
                nullable=False,
            )
            batch_op.create_foreign_key(
                "fk_orders_direccion_entrega_id_delivery_addresses",
                "delivery_addresses",
                ["direccion_entrega_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    else:
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "direccion_entrega_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
            batch_op.alter_column(
                "direccion_snapshot",
                existing_type=sa.String(500),
                nullable=False,
            )
