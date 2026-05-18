"""
Unit tests for payment schemas — payments-non-approved-as-data change.

Runner: cd backend && uv run pytest tests/unit/test_payment_schemas.py -xvs
"""

from __future__ import annotations

import pytest


class TestPagoCreateResponse:
    """TDD RED → GREEN tests for PagoCreateResponse schema."""

    def test_schema_tiene_mp_status(self):
        """PagoCreateResponse expone mp_status como str."""
        from features.payments.schemas import PagoCreateResponse

        r = PagoCreateResponse(
            mp_status="approved",
            mp_id="mp_pay_001",
            status_detail="accredited",
            pago_id=7,
        )
        assert r.mp_status == "approved"

    def test_schema_tiene_mp_id_opcional(self):
        """PagoCreateResponse acepta mp_id=None."""
        from features.payments.schemas import PagoCreateResponse

        r = PagoCreateResponse(
            mp_status="pending",
            mp_id=None,
            status_detail="pending_review_manual",
            pago_id=3,
        )
        assert r.mp_id is None

    def test_schema_tiene_status_detail(self):
        """PagoCreateResponse expone status_detail como str."""
        from features.payments.schemas import PagoCreateResponse

        r = PagoCreateResponse(
            mp_status="rejected",
            mp_id="mp_pay_002",
            status_detail="cc_rejected_insufficient_amount",
            pago_id=5,
        )
        assert r.status_detail == "cc_rejected_insufficient_amount"

    def test_schema_tiene_pago_id(self):
        """PagoCreateResponse expone pago_id como int."""
        from features.payments.schemas import PagoCreateResponse

        r = PagoCreateResponse(
            mp_status="approved",
            mp_id="mp_pay_001",
            status_detail="accredited",
            pago_id=99,
        )
        assert r.pago_id == 99

    def test_schema_from_attributes_false(self):
        """PagoCreateResponse usa ConfigDict(from_attributes=False) — no admite ORM instances directas."""
        from features.payments.schemas import PagoCreateResponse
        from pydantic import ConfigDict

        assert PagoCreateResponse.model_config.get("from_attributes") is False or \
               PagoCreateResponse.model_config.get("from_attributes") is None
