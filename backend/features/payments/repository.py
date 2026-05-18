"""
Payment repository — data access for Pago.

Import chain (regla de oro): repository → models, shared.repository.
No imports from service, router, or FastAPI.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from features.payments.models import Pago
from shared.repository import BaseRepository

# Statuses that block a new payment attempt (RN-PA08, D10)
_ACTIVE_STATUSES = ("approved", "pending", "in_process")


class PaymentRepository(BaseRepository[Pago]):
    """Data access for Pago — payment records and MercadoPago integration fields."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Pago)

    def create_pago(
        self,
        pedido_id: int,
        monto: Decimal,
        forma_pago_codigo: str,
        idempotency_key: str,
        mp_status: str = "pending",
    ) -> Pago:
        """
        Insert a new Pago row and flush (NO commit — caller's UoW commits).

        mp_status: the real status returned by MercadoPago. Pass it explicitly
        so the first INSERT reflects the actual result, not a temporary "pending".
        Default "pending" kept for backward-compat with tests that don't pass it.
        """
        pago = Pago(
            pedido_id=pedido_id,
            monto=monto,
            forma_pago_codigo=forma_pago_codigo,
            idempotency_key=idempotency_key,
            mp_status=mp_status,
        )
        self.session.add(pago)
        self.session.flush()
        self.session.refresh(pago)
        return pago

    def find_by_mp_payment_id(self, mp_payment_id: str) -> Optional[Pago]:
        """Return the Pago whose mp_payment_id matches, or None."""
        stmt = select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def find_latest_by_pedido_id(self, pedido_id: int) -> Optional[Pago]:
        """Return the most recent Pago for a given pedido_id, or None."""
        stmt = (
            select(Pago)
            .where(Pago.pedido_id == pedido_id)
            .order_by(Pago.creado_en.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def find_active_by_pedido_id(self, pedido_id: int) -> Optional[Pago]:
        """
        Return a Pago in an active state (approved, pending, in_process) for the order.

        Used to prevent duplicate payment attempts (D10, RN-PA08).
        """
        stmt = select(Pago).where(
            Pago.pedido_id == pedido_id,
            Pago.mp_status.in_(_ACTIVE_STATUSES),
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def find_by_external_reference(self, external_reference: str) -> Optional[Pago]:
        """
        Return the Pago whose external_reference matches, or None.

        Used for idempotency checks (D12) and webhook reconciliation (D6).
        """
        stmt = select(Pago).where(Pago.external_reference == external_reference)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_mp_fields(
        self,
        pago: Pago,
        mp_payment_id: str,
        mp_status: str,
    ) -> None:
        """
        Update the MercadoPago integration fields on an existing Pago and flush.

        The caller's UoW session commits these changes atomically with any
        other writes in the same transaction (e.g., order state transition).
        """
        pago.mp_payment_id = mp_payment_id
        pago.mp_status = mp_status
        self.session.flush()
