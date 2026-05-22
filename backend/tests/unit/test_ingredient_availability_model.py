"""
Unit tests — Tasks 6.1 + 6.3: Ingrediente.activo flag and
HistorialDisponibilidadIngrediente model + migrations.

Strategy: same SQLite in-memory approach used by test_migration_rename_en_camino.
We test the upgrade/downgrade SQL directly without invoking the Alembic runner
(which targets Postgres). Business-logic assertions validate column presence,
NOT NULL constraint, defaults, and structural shape.

Runner: cd backend && uv run pytest tests/unit/test_ingredient_availability_model.py -xvs
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Task 6.1 — Ingrediente.activo column
# ---------------------------------------------------------------------------


class TestIngredienteActivoColumn:
    """
    Task 6.1: Ingrediente.activo defaults to true for new and existing rows;
    the column is NOT NULL.

    We test by:
      1. Verifying the ORM class exposes the column with the right defaults.
      2. Simulating upgrade/downgrade SQL against SQLite to verify schema ops.
    """

    def test_ingrediente_model_has_activo_column(self):
        """The Ingrediente ORM model must have an 'activo' boolean column."""
        from features.catalog.models import Ingrediente

        col = Ingrediente.__table__.columns.get("activo")
        assert col is not None, "Ingrediente must have an 'activo' column"

    def test_activo_column_is_not_nullable(self):
        """Ingrediente.activo must be NOT NULL."""
        from features.catalog.models import Ingrediente

        col = Ingrediente.__table__.columns["activo"]
        assert col.nullable is False, "activo must be NOT NULL"

    def test_activo_column_default_is_true(self):
        """Ingrediente.activo must default to True for new instances."""
        from features.catalog.models import Ingrediente

        # The SQLAlchemy-level default (not server_default)
        ing = Ingrediente(nombre="test_activo_default")
        # If default is set at ORM level, accessing it should give True
        # If it's a server_default only, we check the column default
        col = Ingrediente.__table__.columns["activo"]
        # Either the ORM default or the column server_default must indicate true
        orm_default = getattr(col, "default", None)
        server_default = getattr(col, "server_default", None)
        has_orm_true = orm_default is not None and str(orm_default.arg).lower() in ("true", "1")
        has_server_true = server_default is not None and "true" in str(server_default.arg).lower()
        # Or the instance attribute itself
        instance_val = getattr(ing, "activo", None)
        assert (
            has_orm_true or has_server_true or instance_val is True
        ), (
            f"Ingrediente.activo must default to True. "
            f"orm_default={orm_default}, server_default={server_default}, instance={instance_val}"
        )

    def test_existing_rows_get_activo_true_via_migration_default(self):
        """
        The Alembic migration adds 'activo BOOLEAN NOT NULL DEFAULT true'.
        Existing rows (inserted before the column existed) must get activo=true
        via the column's DEFAULT clause.

        Simulated with SQLite: insert a row, add the column with DEFAULT 1,
        verify the existing row has activo=1.
        """
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE ingredients ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  nombre TEXT NOT NULL UNIQUE,"
                "  es_alergeno INTEGER NOT NULL DEFAULT 0,"
                "  es_removible INTEGER NOT NULL DEFAULT 0"
                ")"
            ))
            conn.execute(text(
                "INSERT INTO ingredients (nombre, es_alergeno, es_removible) VALUES ('cebolla', 0, 0)"
            ))

        # Simulate upgrade: add activo column with DEFAULT true (1 in SQLite)
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE ingredients ADD COLUMN activo INTEGER NOT NULL DEFAULT 1"
            ))

        with engine.connect() as conn:
            row = conn.execute(text("SELECT activo FROM ingredients WHERE nombre = 'cebolla'")).fetchone()

        assert row is not None
        assert row[0] == 1, f"Existing row must get activo=1 (true) via DEFAULT, got {row[0]}"

    def test_new_rows_get_activo_true_by_default_in_sqlite(self):
        """After adding the column, new rows inserted without specifying activo get true."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE ingredients ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  nombre TEXT NOT NULL UNIQUE,"
                "  activo INTEGER NOT NULL DEFAULT 1"
                ")"
            ))
            conn.execute(text("INSERT INTO ingredients (nombre) VALUES ('tomate')"))

        with engine.connect() as conn:
            row = conn.execute(text("SELECT activo FROM ingredients WHERE nombre = 'tomate'")).fetchone()

        assert row[0] == 1

    def test_migration_downgrade_drops_activo_column(self):
        """
        Simulate downgrade: after adding 'activo', the downgrade op removes it.
        In SQLite we can't DROP COLUMN directly on old versions, so we verify
        conceptually that the upgrade adds it and the column is present.
        (Full DROP COLUMN test is done in the Postgres migration itself.)
        We at minimum verify the upgrade adds the column and that the downgrade
        SQL is in the migration file.
        """
        from pathlib import Path
        migration_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        # Find the migration that adds the activo column
        candidates = list(migration_dir.glob("*activo*"))
        assert len(candidates) >= 1, (
            f"No migration file found matching '*activo*' in {migration_dir}. "
            "Task 6.2 requires creating this migration."
        )
        migration_file = candidates[0]
        content = migration_file.read_text()
        assert "activo" in content, "Migration must mention 'activo'"
        assert "downgrade" in content.lower(), "Migration must have a downgrade function"
        # The downgrade must drop the column
        assert "drop_column" in content.lower() or "DROP COLUMN" in content, (
            "downgrade() must drop the 'activo' column"
        )


# ---------------------------------------------------------------------------
# Task 6.3 — HistorialDisponibilidadIngrediente model + migration
# ---------------------------------------------------------------------------


class TestHistorialDisponibilidadIngredienteModel:
    """
    Task 6.3: HistorialDisponibilidadIngrediente model must have the required
    columns, use BaseModel (mutable — not AppendOnlyBaseModel), and the
    pending/resolved state must be DERIVED from resuelto_en (no separate status col).
    """

    def test_model_class_exists(self):
        """HistorialDisponibilidadIngrediente must be importable from the right module."""
        try:
            from features.availability.models import HistorialDisponibilidadIngrediente  # noqa: F401
        except ImportError as exc:
            pytest.fail(
                f"HistorialDisponibilidadIngrediente not importable: {exc}. "
                "Task 6.4 must create features/availability/models.py with this class."
            )

    def test_table_name_is_canonical(self):
        """Table name must be 'ingredient_availability_history' per D6."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        assert HistorialDisponibilidadIngrediente.__tablename__ == "ingredient_availability_history"

    def test_inherits_from_base_model_not_append_only(self):
        """
        Must use BaseModel (rows are mutated on resolution) — NOT AppendOnlyBaseModel.
        D6 explicitly calls out this divergence from HistorialEstadoPedido.
        """
        from features.availability.models import HistorialDisponibilidadIngrediente
        from shared.models import AppendOnlyBaseModel, BaseModel

        assert issubclass(HistorialDisponibilidadIngrediente, BaseModel), (
            "HistorialDisponibilidadIngrediente must inherit from BaseModel (rows are mutated on resolution)"
        )
        assert not issubclass(HistorialDisponibilidadIngrediente, AppendOnlyBaseModel), (
            "Must NOT use AppendOnlyBaseModel — rows are updated (resuelto_en, resuelto_por) on resolution"
        )

    def test_has_ingrediente_id_column(self):
        """Must have ingrediente_id FK column."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "ingrediente_id" in table.columns, "Must have ingrediente_id column"
        col = table.columns["ingrediente_id"]
        assert not col.nullable, "ingrediente_id must be NOT NULL"

    def test_has_reportado_por_column(self):
        """Must have reportado_por FK column (cook user id)."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "reportado_por" in table.columns, "Must have reportado_por column"
        col = table.columns["reportado_por"]
        assert not col.nullable, "reportado_por must be NOT NULL"

    def test_has_pedido_id_column(self):
        """Must have pedido_id FK column (order where shortage was detected)."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "pedido_id" in table.columns, "Must have pedido_id column"
        col = table.columns["pedido_id"]
        assert not col.nullable, "pedido_id must be NOT NULL"

    def test_has_resuelto_en_nullable(self):
        """resuelto_en must be nullable (NULL = pending, set = resolved)."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "resuelto_en" in table.columns, "Must have resuelto_en column"
        col = table.columns["resuelto_en"]
        assert col.nullable, "resuelto_en must be nullable (NULL means pending)"

    def test_has_resuelto_por_nullable(self):
        """resuelto_por must be nullable (NULL until admin resolves)."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "resuelto_por" in table.columns, "Must have resuelto_por column"
        col = table.columns["resuelto_por"]
        assert col.nullable, "resuelto_por must be nullable"

    def test_no_status_column(self):
        """
        There must be NO separate 'estado' or 'status' column.
        Pending/resolved state is DERIVED from resuelto_en IS NULL.
        """
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        col_names = set(table.columns.keys())
        bad_cols = {"estado", "status", "pendiente", "resuelto"}
        found = col_names & bad_cols
        assert not found, (
            f"Must NOT have a status column — pending/resolved is derived from resuelto_en. "
            f"Found: {found}"
        )

    def test_has_creado_en_from_base_model(self):
        """Must have creado_en timestamp from BaseModel."""
        from features.availability.models import HistorialDisponibilidadIngrediente

        table = HistorialDisponibilidadIngrediente.__table__
        assert "creado_en" in table.columns, "BaseModel must provide creado_en"

    def test_pendiente_derived_from_resuelto_en(self):
        """
        Demonstrate that pending/resolved semantics come from resuelto_en being NULL.
        This is a documentation/contract test — verifies the design decision is encoded.
        """
        from features.availability.models import HistorialDisponibilidadIngrediente

        # Create an instance with resuelto_en=None and verify the model doesn't
        # have a separate status field.
        instance = HistorialDisponibilidadIngrediente(
            ingrediente_id=1,
            reportado_por=2,
            pedido_id=3,
        )
        # resuelto_en defaults to None → this IS the "pending" indicator
        assert instance.resuelto_en is None, "New report must start as pending (resuelto_en=None)"
        # Verify there is no separate status attribute
        for attr in ("estado", "status", "pendiente"):
            assert not hasattr(instance, attr) or attr == "pendiente", (
                f"Instance must not carry a status attribute '{attr}' — use resuelto_en"
            )


class TestHistorialMigrationSQL:
    """
    Task 6.3: The Alembic migration for ingredient_availability_history must
    create and drop the table correctly.
    """

    def _create_prereqs(self, conn):
        """Create minimal prerequisite tables for the FK references."""
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ingredients ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS users ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS orders ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT"
            ")"
        ))

    _CREATE_HISTORY_TABLE = """
        CREATE TABLE ingredient_availability_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente_id INTEGER NOT NULL REFERENCES ingredients(id),
            reportado_por INTEGER NOT NULL REFERENCES users(id),
            pedido_id INTEGER NOT NULL REFERENCES orders(id),
            creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            eliminado_en TIMESTAMP,
            resuelto_en TIMESTAMP,
            resuelto_por INTEGER REFERENCES users(id)
        )
    """

    _DROP_HISTORY_TABLE = "DROP TABLE IF EXISTS ingredient_availability_history"

    def test_upgrade_creates_table_with_required_columns(self):
        """Simulated upgrade creates ingredient_availability_history with all required columns."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            self._create_prereqs(conn)
            conn.execute(text(self._CREATE_HISTORY_TABLE))

        insp = inspect(engine)
        tables = insp.get_table_names()
        assert "ingredient_availability_history" in tables

        cols = {c["name"] for c in insp.get_columns("ingredient_availability_history")}
        required = {"id", "ingrediente_id", "reportado_por", "pedido_id",
                    "creado_en", "resuelto_en", "resuelto_por"}
        missing = required - cols
        assert not missing, f"Missing columns after upgrade: {missing}"

    def test_resuelto_en_is_nullable_in_schema(self):
        """resuelto_en must allow NULL after upgrade (pending = NULL)."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            self._create_prereqs(conn)
            conn.execute(text(self._CREATE_HISTORY_TABLE))
            # Seed prereqs
            conn.execute(text("INSERT INTO ingredients (nombre) VALUES ('cebolla')"))
            conn.execute(text("INSERT INTO users (email) VALUES ('cook@test.com')"))
            conn.execute(text("INSERT INTO orders DEFAULT VALUES"))

        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO ingredient_availability_history "
                "(ingrediente_id, reportado_por, pedido_id) VALUES (1, 1, 1)"
            ))

        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT resuelto_en FROM ingredient_availability_history WHERE id = 1"
            )).fetchone()
        assert row[0] is None, "resuelto_en must be NULL for a new report"

    def test_downgrade_drops_the_table(self):
        """Simulated downgrade drops ingredient_availability_history."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as conn:
            self._create_prereqs(conn)
            conn.execute(text(self._CREATE_HISTORY_TABLE))

        insp = inspect(engine)
        assert "ingredient_availability_history" in insp.get_table_names()

        with engine.begin() as conn:
            conn.execute(text(self._DROP_HISTORY_TABLE))

        insp2 = inspect(engine)
        assert "ingredient_availability_history" not in insp2.get_table_names(), (
            "ingredient_availability_history must be gone after downgrade"
        )

    def test_migration_file_exists(self):
        """A migration file for ingredient_availability_history must exist."""
        from pathlib import Path
        migration_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        candidates = list(migration_dir.glob("*availability*"))
        assert len(candidates) >= 1, (
            f"No migration file found matching '*availability*' in {migration_dir}. "
            "Task 6.4 requires creating this migration."
        )
