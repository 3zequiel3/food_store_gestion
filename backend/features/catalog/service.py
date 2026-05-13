"""
Catalog service — read-only operations for reference data.

All functions use UnitOfWork for consistency with the project's service layer.
Even pure reads go through UoW so that the test monkeypatch (conftest) works
correctly and session lifecycle is uniform across all services.
"""

from __future__ import annotations

from typing import List

from sqlalchemy import select

from backend.features.catalog.models import FormaPago
from backend.shared.unit_of_work import UnitOfWork


def listar_formas_pago() -> List[FormaPago]:
    """
    Return all enabled payment methods ordered by id.

    Only formas with habilitada=True are returned (for selectors in checkout).
    """
    with UnitOfWork() as uow:
        stmt = (
            select(FormaPago)
            .where(FormaPago.habilitada.is_(True))
            .order_by(FormaPago.id)
        )
        return list(uow.session.execute(stmt).scalars().all())
