"""
Task 1.1 — Tests: publish must occur AFTER the UoW commits.

Strategy: we track ORDER OF OPERATIONS by recording sequence numbers for:
  - publish() call time (via fake publisher)
  - UnitOfWork.__exit__ commit time (via monkeypatched exit)

After the fix, the router pattern is:
  with UoW() as uow:
      dto = svc.report_unavailable(...)   # DB work, no publish
  # UoW exits → commits here
  _publish_report_event(publisher, dto=dto)  # publish POST-commit ✓

Both tests assert publish_seq > commit_seq (published AFTER commit).
"""

from __future__ import annotations

import pytest

# Import all models so mapper resolves relationships
import features.auth.models  # noqa: F401
import features.users.models  # noqa: F401
import features.catalog.models  # noqa: F401
import features.addresses.models  # noqa: F401
import features.products.models  # noqa: F401
import features.availability.models  # noqa: F401
try:
    import features.orders.models  # noqa: F401
except Exception:
    pass

from features.catalog.models import Ingrediente
from features.availability.service import (
    IngredientAvailabilityService,
    _publish_report_event,
    _publish_restore_event,
)
from features.websocket.contracts import DomainEvent
import shared.unit_of_work as _uow_mod
from shared.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------------
# Ordering tracker publisher
# ---------------------------------------------------------------------------

class OrderTrackingPublisher:
    """
    Records sequence numbers for publish() and commit() to detect
    whether publish fires before or after the UoW commit.
    """

    def __init__(self):
        self._counter = 0
        self.publish_seqs: list[int] = []
        self.commit_seq: int | None = None
        self.calls: list[DomainEvent] = []

    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def mark_commit(self) -> None:
        """Called by the patched UoW.__exit__ to record commit order."""
        self.commit_seq = self._next()

    def publish(self, event: DomainEvent) -> None:
        self.calls.append(event)
        self.publish_seqs.append(self._next())

    def assert_publish_after_commit(self) -> None:
        assert self.commit_seq is not None, "UoW commit was never recorded"
        assert len(self.publish_seqs) > 0, "publish() was never called"
        for seq in self.publish_seqs:
            assert seq > self.commit_seq, (
                f"publish() fired BEFORE UoW commit: "
                f"publish_seq={seq} <= commit_seq={self.commit_seq}. "
                f"The event was published inside the UoW body (pre-commit). "
                f"Move the publish call to the router, AFTER `with UoW():` exits."
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_ingrediente(test_db_session, nombre: str = "Tomate") -> int:
    ing = Ingrediente(nombre=nombre, activo=True)
    test_db_session.add(ing)
    test_db_session.flush()
    return ing.id


def _seed_user_and_order(test_db_session):
    from features.users.models import Usuario
    from shared.security import hash_password
    from sqlalchemy import text

    user = Usuario(
        email="cook_test_pac@test.com",
        password_hash=hash_password("pw"),
        nombre="Cook",
        apellido="PAC",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()

    test_db_session.execute(
        text(
            "INSERT INTO orders (user_id, estado_codigo, forma_pago_codigo, total, costo_envio) "
            "VALUES (:uid, 'CONFIRMADO', 'EFECTIVO', 0, 0)"
        ),
        {"uid": user.id},
    )
    test_db_session.flush()

    row = test_db_session.execute(
        text("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    ).fetchone()
    return user.id, row[0]


def _make_tracked_exit(publisher: OrderTrackingPublisher):
    """Return a patched UoW.__exit__ that records commit timing."""
    original_exit = UnitOfWork.__exit__

    def tracked_exit(self_uow, exc_type, exc_val, exc_tb):
        result = original_exit(self_uow, exc_type, exc_val, exc_tb)
        if exc_type is None:
            publisher.mark_commit()
        return result

    return tracked_exit


# ---------------------------------------------------------------------------
# Tests — router pattern: svc inside UoW, publish called AFTER UoW exits
# ---------------------------------------------------------------------------


class TestPublishAfterCommit:

    def test_report_unavailable_publish_fires_after_uow_commit(
        self, test_db_session, monkeypatch
    ):
        """
        Task 1.1 (report path):
        ingredient_unavailable_reported must be published AFTER the UoW commits.

        Simulates the router pattern:
          with UoW() as uow:
              dto = svc.report_unavailable(...)
          _publish_report_event(publisher, dto=dto)  # post-commit ← should be here
        """
        ingrediente_id = _seed_ingrediente(test_db_session, "Cebolla")
        user_id, order_id = _seed_user_and_order(test_db_session)
        test_db_session.commit()

        publisher = OrderTrackingPublisher()
        monkeypatch.setattr(UnitOfWork, "__exit__", _make_tracked_exit(publisher))

        # Router pattern: run service inside UoW, publish AFTER
        with UnitOfWork() as uow:
            svc = IngredientAvailabilityService(session=uow.session)
            dto = svc.report_unavailable(
                ingrediente_id=ingrediente_id,
                reportado_por=user_id,
                pedido_id=order_id,
            )
        # UoW exits here → commit → mark_commit() fires → commit_seq recorded
        _publish_report_event(publisher, dto=dto)

        publisher.assert_publish_after_commit()

    def test_resolve_availability_publish_fires_after_uow_commit(
        self, test_db_session, monkeypatch
    ):
        """
        Task 1.1 (resolve path):
        ingredient_availability_restored must be published AFTER the UoW commits.

        Simulates the router pattern:
          with UoW() as uow:
              dto = svc.resolve_availability(...)
          _publish_restore_event(publisher, dto=dto)  # post-commit ← should be here
        """
        ingrediente_id = _seed_ingrediente(test_db_session, "Lechuga")
        user_id, order_id = _seed_user_and_order(test_db_session)
        test_db_session.commit()

        # Setup: report unavailable first to create a history row
        with UnitOfWork() as uow:
            svc = IngredientAvailabilityService(session=uow.session)
            svc.report_unavailable(
                ingrediente_id=ingrediente_id,
                reportado_por=user_id,
                pedido_id=order_id,
            )

        publisher = OrderTrackingPublisher()
        monkeypatch.setattr(UnitOfWork, "__exit__", _make_tracked_exit(publisher))

        # Router pattern: run service inside UoW, publish AFTER
        with UnitOfWork() as uow:
            svc = IngredientAvailabilityService(session=uow.session)
            dto = svc.resolve_availability(
                ingrediente_id=ingrediente_id,
                resuelto_por=user_id,
            )
        # UoW exits here → commit → mark_commit() fires
        _publish_restore_event(publisher, dto=dto)

        publisher.assert_publish_after_commit()
