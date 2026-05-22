"""
Unit tests — Tasks 6.5, 6.7, 6.9: IngredientAvailabilityService
(report, resolve, and query operations).

All tests are pure-unit: they operate against SQLite in-memory via the
conftest UoW monkeypatch (same pattern as other unit tests), or mock the
UoW where DB wiring is the concern (isolation tests).

Design D6:
- report_unavailable: UoW — set activo=False + insert history row. Then publish
  ingredient_unavailable_reported to orders:all (best-effort).
- resolve_availability: UoW — set activo=True + bulk-close all open rows for
  the ingredient. Then publish ingredient_availability_restored to kitchen:all (best-effort).
- Queries: open shortages (resuelto_en IS NULL), resolved history.

Runner: cd backend && uv run pytest tests/unit/test_ingredient_availability_service.py -xvs
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from shared.database import Base


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite with real ORM schema
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sqlite_engine():
    """Minimal SQLite engine with the tables needed for availability tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import models so metadata is populated
    import features.catalog.models  # noqa: F401
    import features.availability.models  # noqa: F401
    # We only create the tables we need — users, ingredients, orders, history
    # SQLite is more lenient about FK constraints (disabled by default)
    Base.metadata.create_all(engine, tables=[
        Base.metadata.tables["ingredients"],
        Base.metadata.tables["ingredient_availability_history"],
    ])
    return engine


@pytest.fixture()
def db_session(sqlite_engine):
    """A fresh session per test — rolls back after each test for isolation."""
    connection = sqlite_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    trans.rollback()
    connection.close()


def _make_ingrediente(session: Session, *, nombre: str = "cebolla", activo: bool = True):
    """Insert a minimal Ingrediente row and return the ORM object."""
    from features.catalog.models import Ingrediente

    ing = Ingrediente(nombre=nombre, es_alergeno=False, es_removible=False, activo=activo)
    session.add(ing)
    session.flush()
    return ing


def _make_history_row(
    session: Session,
    *,
    ingrediente_id: int,
    reportado_por: int = 10,
    pedido_id: int = 100,
    resuelto_en=None,
    resuelto_por=None,
):
    """Insert a HistorialDisponibilidadIngrediente row and return it."""
    from features.availability.models import HistorialDisponibilidadIngrediente

    row = HistorialDisponibilidadIngrediente(
        ingrediente_id=ingrediente_id,
        reportado_por=reportado_por,
        pedido_id=pedido_id,
        resuelto_en=resuelto_en,
        resuelto_por=resuelto_por,
    )
    session.add(row)
    session.flush()
    return row


# ---------------------------------------------------------------------------
# Task 6.5 — report_unavailable: sets activo=False AND inserts history row
# ---------------------------------------------------------------------------


class TestReportUnavailable:
    """
    Task 6.5: reporting an ingredient unavailable sets activo=False AND appends
    one HistorialDisponibilidadIngrediente row (resuelto_en=NULL) inside ONE UoW.
    """

    def test_report_sets_activo_false(self, db_session):
        """After report_unavailable, Ingrediente.activo must be False."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, activo=True)

        svc = IngredientAvailabilityService(session=db_session)
        svc.report_unavailable(
            ingrediente_id=ing.id,
            reportado_por=10,
            pedido_id=100,
        )
        db_session.flush()

        db_session.refresh(ing)
        assert ing.activo is False, f"activo must be False after report, got {ing.activo}"

    def test_report_inserts_history_row(self, db_session):
        """After report_unavailable, one HistorialDisponibilidadIngrediente row must exist."""
        from features.availability.models import HistorialDisponibilidadIngrediente
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="tomate", activo=True)

        svc = IngredientAvailabilityService(session=db_session)
        svc.report_unavailable(
            ingrediente_id=ing.id,
            reportado_por=10,
            pedido_id=100,
        )
        db_session.flush()

        rows = (
            db_session.query(HistorialDisponibilidadIngrediente)
            .filter_by(ingrediente_id=ing.id)
            .all()
        )
        assert len(rows) == 1, f"Expected 1 history row, got {len(rows)}"

    def test_report_history_row_is_pending(self, db_session):
        """The inserted history row must have resuelto_en=NULL (pending)."""
        from features.availability.models import HistorialDisponibilidadIngrediente
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="lechuga", activo=True)

        svc = IngredientAvailabilityService(session=db_session)
        svc.report_unavailable(
            ingrediente_id=ing.id,
            reportado_por=10,
            pedido_id=100,
        )
        db_session.flush()

        row = (
            db_session.query(HistorialDisponibilidadIngrediente)
            .filter_by(ingrediente_id=ing.id)
            .first()
        )
        assert row is not None
        assert row.resuelto_en is None, "New report must start as pending (resuelto_en=NULL)"
        assert row.pedido_id == 100
        assert row.reportado_por == 10

    def test_report_publishes_event_post_commit(self):
        """
        report_unavailable must call publish() on the event publisher with
        ingredient_unavailable_reported event targeting 'orders:all'.
        The publish is best-effort and must not raise even if no admin is connected.
        """
        from features.availability.service import IngredientAvailabilityService

        session = MagicMock()
        # Simulate the Ingrediente ORM row
        fake_ing = MagicMock()
        fake_ing.id = 7
        fake_ing.activo = True
        fake_ing.nombre = "cebolla"
        session.get.return_value = fake_ing

        mock_publisher = MagicMock()

        svc = IngredientAvailabilityService(session=session, publisher=mock_publisher)
        svc.report_unavailable(ingrediente_id=7, reportado_por=10, pedido_id=100)

        mock_publisher.publish.assert_called_once()
        event = mock_publisher.publish.call_args.args[0]
        assert event.type == "ingredient_unavailable_reported"
        assert event.topic == "orders:all"
        assert event.payload["ingrediente_id"] == 7

    def test_report_survives_with_no_publisher(self, db_session):
        """
        Reporting must succeed even if no publisher is wired (no admin connected).
        The service must not raise when publisher is None or publish() fails.
        """
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="zanahoria", activo=True)

        # publisher=None → best-effort, must not raise
        svc = IngredientAvailabilityService(session=db_session, publisher=None)
        try:
            svc.report_unavailable(
                ingrediente_id=ing.id,
                reportado_por=10,
                pedido_id=100,
            )
        except Exception as exc:
            pytest.fail(f"report_unavailable raised with no publisher: {exc}")


# ---------------------------------------------------------------------------
# Task 6.7 — resolve_availability: sets activo=True AND bulk-closes all open rows
# ---------------------------------------------------------------------------


class TestResolveAvailability:
    """
    Task 6.7: resolving an ingredient shortage sets activo=True AND bulk-closes
    ALL open rows for that ingredient (resuelto_en + resuelto_por on every
    resuelto_en IS NULL row) inside ONE UoW. Resolved rows are retained.
    """

    def test_resolve_sets_activo_true(self, db_session):
        """After resolve_availability, Ingrediente.activo must be True."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="papas", activo=False)

        svc = IngredientAvailabilityService(session=db_session)
        svc.resolve_availability(ingrediente_id=ing.id, resuelto_por=2)
        db_session.flush()

        db_session.refresh(ing)
        assert ing.activo is True, f"activo must be True after resolve, got {ing.activo}"

    def test_resolve_bulk_closes_all_open_rows(self, db_session):
        """All open rows (resuelto_en IS NULL) for the ingredient must be closed."""
        from features.availability.models import HistorialDisponibilidadIngrediente
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="espinaca", activo=False)
        # Two open rows
        _make_history_row(db_session, ingrediente_id=ing.id, pedido_id=101)
        _make_history_row(db_session, ingrediente_id=ing.id, pedido_id=102)

        svc = IngredientAvailabilityService(session=db_session)
        svc.resolve_availability(ingrediente_id=ing.id, resuelto_por=2)
        db_session.flush()

        open_rows = (
            db_session.query(HistorialDisponibilidadIngrediente)
            .filter(
                HistorialDisponibilidadIngrediente.ingrediente_id == ing.id,
                HistorialDisponibilidadIngrediente.resuelto_en.is_(None),
            )
            .all()
        )
        assert len(open_rows) == 0, (
            f"All open rows must be closed after resolve. Still open: {len(open_rows)}"
        )

    def test_resolve_sets_resuelto_por_on_closed_rows(self, db_session):
        """Closed rows must carry the admin's user id in resuelto_por."""
        from features.availability.models import HistorialDisponibilidadIngrediente
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="pimiento", activo=False)
        _make_history_row(db_session, ingrediente_id=ing.id)

        svc = IngredientAvailabilityService(session=db_session)
        svc.resolve_availability(ingrediente_id=ing.id, resuelto_por=99)
        db_session.flush()

        row = (
            db_session.query(HistorialDisponibilidadIngrediente)
            .filter_by(ingrediente_id=ing.id)
            .first()
        )
        assert row.resuelto_por == 99
        assert row.resuelto_en is not None

    def test_resolve_retains_already_resolved_rows(self, db_session):
        """Rows that were already resolved (from a prior cycle) must be retained intact."""
        from features.availability.models import HistorialDisponibilidadIngrediente
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="berenjena", activo=False)
        # One already-resolved row (from a prior unavailability cycle)
        old_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        _make_history_row(
            db_session,
            ingrediente_id=ing.id,
            pedido_id=50,
            resuelto_en=old_ts,
            resuelto_por=1,
        )
        # One open row from the current cycle
        _make_history_row(db_session, ingrediente_id=ing.id, pedido_id=51)

        svc = IngredientAvailabilityService(session=db_session)
        svc.resolve_availability(ingrediente_id=ing.id, resuelto_por=2)
        db_session.flush()

        all_rows = (
            db_session.query(HistorialDisponibilidadIngrediente)
            .filter_by(ingrediente_id=ing.id)
            .all()
        )
        assert len(all_rows) == 2, "Resolved rows must be retained (audit)"

        # The old row must be unchanged.
        # SQLite strips timezone info on round-trip, so compare naive timestamps.
        old_row = next(r for r in all_rows if r.pedido_id == 50)
        old_row_ts = old_row.resuelto_en
        if old_row_ts is not None and old_row_ts.tzinfo is None:
            old_row_ts = old_row_ts.replace(tzinfo=timezone.utc)
        assert old_row_ts == old_ts
        assert old_row.resuelto_por == 1

    def test_resolve_publishes_event_post_commit(self):
        """
        resolve_availability must publish ingredient_availability_restored
        to kitchen:all (best-effort) so the cook is notified.
        """
        from features.availability.service import IngredientAvailabilityService

        session = MagicMock()
        fake_ing = MagicMock()
        fake_ing.id = 7
        fake_ing.activo = False
        fake_ing.nombre = "cebolla"
        session.get.return_value = fake_ing
        # bulk-close query returns 0 rows affected
        session.execute.return_value.rowcount = 0

        mock_publisher = MagicMock()

        svc = IngredientAvailabilityService(session=session, publisher=mock_publisher)
        svc.resolve_availability(ingrediente_id=7, resuelto_por=2)

        mock_publisher.publish.assert_called_once()
        event = mock_publisher.publish.call_args.args[0]
        assert event.type == "ingredient_availability_restored"
        assert event.topic == "kitchen:all"
        assert event.payload["ingrediente_id"] == 7

    def test_resolve_survives_publisher_failure(self, db_session):
        """Resolve must not raise if the publisher raises."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="chile", activo=False)
        _make_history_row(db_session, ingrediente_id=ing.id)

        # Publisher that raises
        bad_publisher = MagicMock()
        bad_publisher.publish.side_effect = RuntimeError("network down")

        svc = IngredientAvailabilityService(session=db_session, publisher=bad_publisher)
        try:
            svc.resolve_availability(ingrediente_id=ing.id, resuelto_por=2)
        except Exception as exc:
            pytest.fail(f"resolve_availability raised when publisher failed: {exc}")


# ---------------------------------------------------------------------------
# Task 6.9 — open-shortages and resolved-history queries
# ---------------------------------------------------------------------------


class TestAvailabilityQueries:
    """
    Task 6.9: The query helpers must correctly filter by resuelto_en IS NULL
    (open shortages) and resuelto_en IS NOT NULL (resolved history).
    """

    def test_open_shortages_returns_only_pending_rows(self, db_session):
        """get_open_shortages() must return only rows where resuelto_en IS NULL."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="query_open_test")
        # One open row
        _make_history_row(db_session, ingrediente_id=ing.id, pedido_id=200)
        # One resolved row
        _make_history_row(
            db_session,
            ingrediente_id=ing.id,
            pedido_id=201,
            resuelto_en=datetime(2026, 1, 1, tzinfo=timezone.utc),
            resuelto_por=1,
        )

        svc = IngredientAvailabilityService(session=db_session)
        rows = svc.get_open_shortages()

        # Filter to our ingredient (others may exist from prior tests in module scope)
        our_rows = [r for r in rows if r.ingrediente_id == ing.id]
        assert len(our_rows) == 1, f"Expected 1 open shortage, got {len(our_rows)}"
        assert our_rows[0].resuelto_en is None

    def test_open_shortages_excludes_resolved(self, db_session):
        """get_open_shortages() must never return rows where resuelto_en IS NOT NULL."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="only_resolved_test")
        # Only resolved rows
        _make_history_row(
            db_session,
            ingrediente_id=ing.id,
            pedido_id=300,
            resuelto_en=datetime(2026, 2, 1, tzinfo=timezone.utc),
            resuelto_por=1,
        )

        svc = IngredientAvailabilityService(session=db_session)
        rows = svc.get_open_shortages()

        our_rows = [r for r in rows if r.ingrediente_id == ing.id]
        assert len(our_rows) == 0, "Resolved rows must not appear in open shortages"

    def test_resolved_history_returns_only_closed_rows(self, db_session):
        """get_resolved_history() must return only rows where resuelto_en IS NOT NULL."""
        from features.availability.service import IngredientAvailabilityService

        ing = _make_ingrediente(db_session, nombre="query_resolved_test")
        ts = datetime(2026, 3, 1, tzinfo=timezone.utc)
        _make_history_row(
            db_session,
            ingrediente_id=ing.id,
            pedido_id=400,
            resuelto_en=ts,
            resuelto_por=5,
        )
        # One pending — must not appear
        _make_history_row(db_session, ingrediente_id=ing.id, pedido_id=401)

        svc = IngredientAvailabilityService(session=db_session)
        rows = svc.get_resolved_history()

        our_rows = [r for r in rows if r.ingrediente_id == ing.id]
        assert len(our_rows) == 1, f"Expected 1 resolved row, got {len(our_rows)}"
        # SQLite strips timezone info on round-trip — compare date only
        row_ts = our_rows[0].resuelto_en
        assert row_ts is not None, "resuelto_en must be set on resolved row"
        assert row_ts.year == ts.year and row_ts.month == ts.month and row_ts.day == ts.day
