"""
Pytest configuration and fixtures for Food Store  

Provides fixtures for:
- Test database session
- Test FastAPI client
- Test user and data factories
- Order-domain fixtures: sample_estados_pedido, sample_formas_pago,
  sample_producto_disponible, sample_address (added for order-creation-backend #14)

Markers:
  pg_only — tests that require PostgreSQL (ARRAY(Integer) used in order_items — D2).
             Skipped automatically when DATABASE_URL does not point to Postgres
             or when --pg flag is not passed to pytest.
             Registered in pytest.ini to avoid warnings.
"""

from contextlib import asynccontextmanager
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import shared.unit_of_work as _uow_mod

from main import app
from shared.database import Base

# Import ALL models so SQLAlchemy's declarative registry can resolve
# string-based relationship targets (e.g. relationship("Pedido", ...)).
# Without these imports, mapper configuration fails with KeyError when
# loading fixtures that instantiate related models.
# NOTE: orders/models.py has ARRAY(Integer) — PostgreSQL-specific.
# We import it for mapper registration but skip create_all for that table.
import features.auth.models  # noqa: F401
import features.users.models  # noqa: F401
import features.catalog.models  # noqa: F401
import features.addresses.models  # noqa: F401
import features.products.models  # noqa: F401
import features.payments.models  # noqa: F401
try:
    import features.orders.models  # noqa: F401
except Exception:
    pass  # Imported for mapper registration; table creation skipped below.


# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@asynccontextmanager
async def _null_lifespan(app):
    """No-op lifespan context for tests — table creation is handled by conftest."""
    yield


def _sqlite_compatible_tables(metadata, engine):
    """Return only the tables that SQLite can create (no PG-specific types)."""
    pg_only = {"order_items"}  # Uses ARRAY(Integer) which SQLite doesn't support
    return [t for name, t in metadata.tables.items() if name not in pg_only]


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create only SQLite-compatible tables (skip PG-specific ones like order_items)
    tables = _sqlite_compatible_tables(Base.metadata, engine)
    Base.metadata.create_all(bind=engine, tables=tables)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine, tables=tables)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Session:
    """Create a test database session."""
    connection = test_db_engine.connect()
    transaction = connection.begin()

    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _patch_uow_session_factory(monkeypatch, test_db_session: Session):
    """Patch UnitOfWork's get_session_factory so that services creating UnitOfWork()
    receive a session that uses the in-memory SQLite connection instead of opening
    a real Postgres connection.

    Each UnitOfWork() gets its own Session instance bound to the same connection
    as test_db_session. This keeps their identity maps separate so that test
    fixtures (e.g. sample_user) remain persistent in test_db_session even after
    the service's UoW commits (SAVEPOINT release) its own session.

    autouse=True means this fixture applies to every test automatically.
    The monkeypatch is reverted at teardown by pytest.
    """
    # Obtain the underlying connection that test_db_session is bound to.
    connection = test_db_session.get_bind()

    # Create a sessionmaker for UoW sessions: same connection, separate identity maps.
    #
    # expire_on_commit=False — PRODUCTION PARITY, NOT A SQLITE WORKAROUND.
    # This value mirrors the production sessionmaker in backend/shared/database.py.
    # Production uses expire_on_commit=False so that ORM entities returned by
    # services survive the UoW commit + session close long enough for Pydantic
    # to call model_validate() on them. Without it, SQLAlchemy's default (True)
    # expires all attributes at commit time; the subsequent close() detaches the
    # object, and any attribute read by Pydantic raises DetachedInstanceError.
    #
    # DO NOT remove expire_on_commit=False from here — doing so would break
    # the tests↔production parity and mask future regressions on this axis.
    # See openspec/changes/fix-detached-instance-error-postgres/design.md — D5.
    _UoWSessionFactory = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=connection,
    )

    def _make_test_session_factory():
        """Return a factory that creates new UoW sessions bound to the test connection.

        Each UnitOfWork() used by a service gets its own Session (with its own
        identity map) bound to the same SQLite connection as test_db_session.

        Properties of these UoW sessions:
        - expire_on_commit=False: ORM attributes stay accessible after the UoW
          closes the session, preventing DetachedInstanceError on model_validate.
        - After commit: test_db_session.expire_all() is called so that subsequent
          queries from test_db_session (e.g. auth/login lookups) see the fresh
          data written by the UoW, not stale cached objects.
        """
        def _factory():
            uow_session = _UoWSessionFactory()

            # Patch the session's commit to also expire test_db_session objects,
            # ensuring test assertions and subsequent requests see data changed by
            # this UoW's transaction.
            original_commit = uow_session.commit

            def _commit_and_expire():
                original_commit()
                test_db_session.expire_all()

            uow_session.commit = _commit_and_expire  # type: ignore[method-assign]
            return uow_session

        return _factory

    monkeypatch.setattr(_uow_mod, "get_session_factory", _make_test_session_factory)


@pytest.fixture(scope="function")
def client(test_db_session: Session) -> TestClient:
    """Create a test client with dependency override and rate limiter disabled."""
    from shared.rate_limiter import limiter

    # Disable rate limiting for tests — each test runs independently and
    # all requests come from the same "testclient" IP, causing false 429s.
    original_enabled = limiter.enabled
    limiter.enabled = False

    # Save and replace the lifespan context — the conftest already creates
    # tables (with SQLite-compatible filtering), so the app's lifespan would
    # try to re-create them and fail on PG-specific types (ARRAY).
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _null_lifespan

    with TestClient(app) as test_client:
        yield test_client

    app.router.lifespan_context = original_lifespan
    limiter.enabled = original_enabled
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_roles(test_db_session: Session):
    """Create standard roles for testing."""
    from features.catalog.models import Rol

    roles = [
        Rol(id=1, codigo="ADMIN", descripcion="Administrator"),
        Rol(id=2, codigo="STOCK", descripcion="Stock Manager"),
        Rol(id=3, codigo="PEDIDOS", descripcion="Orders Manager"),
        Rol(id=4, codigo="CLIENT", descripcion="Client"),
    ]
    for role in roles:
        test_db_session.add(role)
    test_db_session.commit()

    return roles


@pytest.fixture(scope="function")
def sample_user(test_db_session: Session, sample_roles):
    """Create a sample user for testing."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="test@example.com",
        password_hash=hash_password("test_password_123"),
        nombre="Test",
        apellido="User",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()

    # Assign CLIENT role
    user_role = UsuarioRol(user_id=user.id, role_id=4)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture
def auth_headers(client, sample_user):
    """Authenticate the TestClient via auth cookies and return no extra headers."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "test_password_123",
        },
    )
    assert response.status_code == 200
    return {}


# ---------------------------------------------------------------------------
# Order-domain fixtures (added for order-creation-backend #14)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def sample_estados_pedido(test_db_session: Session):
    """
    Seed the 6 order states required by FK constraints in the orders table.

    States match the seed data defined in database-schema-seed:
    PENDIENTE(1), CONFIRMADO(2), EN_PREPARACION(3),
    TERMINADO(4), ENTREGADO(5, terminal), CANCELADO(6, terminal).
    """
    from features.catalog.models import EstadoPedido

    estados = [
        EstadoPedido(codigo="PENDIENTE", descripcion="Pendiente de confirmación", orden=1, es_terminal=False),
        EstadoPedido(codigo="CONFIRMADO", descripcion="Confirmado", orden=2, es_terminal=False),
        EstadoPedido(codigo="EN_PREPARACION", descripcion="En preparación", orden=3, es_terminal=False),
        EstadoPedido(codigo="TERMINADO", descripcion="Listo para retirar/entregar", orden=4, es_terminal=False),
        EstadoPedido(codigo="ENTREGADO", descripcion="Entregado", orden=5, es_terminal=True),
        EstadoPedido(codigo="CANCELADO", descripcion="Cancelado", orden=6, es_terminal=True),
    ]
    for estado in estados:
        test_db_session.add(estado)
    test_db_session.commit()
    return estados


@pytest.fixture(scope="function")
def sample_formas_pago(test_db_session: Session):
    """
    Seed the 3 payment methods: MERCADOPAGO, EFECTIVO, TRANSFERENCIA.

    All enabled (habilitada=True) by default.
    Tests that need a disabled method modify the instance directly.
    """
    from features.catalog.models import FormaPago

    formas = [
        FormaPago(codigo="MERCADOPAGO", descripcion="MercadoPago", habilitada=True),
        FormaPago(codigo="EFECTIVO", descripcion="Efectivo", habilitada=True),
        FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia bancaria", habilitada=True),
    ]
    for forma in formas:
        test_db_session.add(forma)
    test_db_session.commit()
    return formas


@pytest.fixture(scope="function")
def sample_producto_disponible(test_db_session: Session):
    """
    Create a single available product with stock=10 and price=100.00.

    Useful as the default product in order tests.
    Tests that need different prices create their own Producto instances.
    """
    from decimal import Decimal
    from features.products.models import Producto

    producto = Producto(
        nombre="Producto Test",
        precio=Decimal("100.00"),
        stock_cantidad=10,
        disponible=True,
    )
    test_db_session.add(producto)
    test_db_session.commit()
    test_db_session.refresh(producto)
    return producto


@pytest.fixture(scope="function")
def sample_address(test_db_session: Session, sample_user):
    """
    Create a delivery address belonging to sample_user.

    Uses the same pattern as _seed_address in test_delivery_addresses.py.
    """
    from features.addresses.models import DireccionEntrega

    addr = DireccionEntrega(
        user_id=sample_user.id,
        calle="Av Siempre Viva",
        numero="742",
        ciudad="Springfield",
        codigo_postal="1000",
        es_principal=True,
    )
    test_db_session.add(addr)
    test_db_session.commit()
    test_db_session.refresh(addr)
    return addr


# ---------------------------------------------------------------------------
# pg_only marker — skip tests that require PostgreSQL in SQLite-only envs
# ---------------------------------------------------------------------------

def _postgres_available() -> bool:
    """
    Detect if PostgreSQL is available for testing.

    Checks DATABASE_URL env var for a postgres/postgresql URL.
    In local dev with the PG container running, DATABASE_URL should be set.
    In CI without PG service, these tests are skipped gracefully.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    return "postgres" in db_url.lower()


def pytest_collection_modifyitems(config, items):
    """
    Skip pg_only tests when PostgreSQL is not available.

    D2: order_items uses ARRAY(Integer) which SQLite doesn't support.
    Tests that insert into order_items must be marked @pytest.mark.pg_only
    and will be skipped in SQLite-only environments.
    """
    if not _postgres_available():
        skip_pg = pytest.mark.skip(
            reason="Requires PostgreSQL (ARRAY(Integer) — D2). "
                   "Set DATABASE_URL to a postgres:// URL or run with --pg to enable."
        )
        for item in items:
            if "pg_only" in item.keywords:
                item.add_marker(skip_pg)
