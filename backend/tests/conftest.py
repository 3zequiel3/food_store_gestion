"""
Pytest configuration and fixtures for Food Store backend.

Provides fixtures for:
- Test database session
- Test FastAPI client
- Test user and data factories
"""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import backend.shared.unit_of_work as _uow_mod

from backend.main import app
from backend.shared.database import Base, get_db
from backend.dependencies import get_uow
from backend.shared.unit_of_work import UnitOfWork

# Import ALL models so SQLAlchemy's declarative registry can resolve
# string-based relationship targets (e.g. relationship("Pedido", ...)).
# Without these imports, mapper configuration fails with KeyError when
# loading fixtures that instantiate related models.
# NOTE: orders/models.py has ARRAY(Integer) — PostgreSQL-specific.
# We import it for mapper registration but skip create_all for that table.
import backend.features.auth.models  # noqa: F401
import backend.features.users.models  # noqa: F401
import backend.features.catalog.models  # noqa: F401
import backend.features.addresses.models  # noqa: F401
import backend.features.products.models  # noqa: F401
import backend.features.payments.models  # noqa: F401
try:
    import backend.features.orders.models  # noqa: F401
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
    """Patch UnitOfWork.get_session_factory so that services creating UnitOfWork()
    with no arguments receive a session that uses the in-memory SQLite connection
    instead of opening a real Postgres connection.

    Each UnitOfWork() gets its own Session instance bound to the same connection
    as test_db_session. This keeps their identity maps separate so that test
    fixtures (e.g. sample_user) remain persistent in test_db_session even after
    the service's UoW commits (SAVEPOINT release) its own session.

    autouse=True means this fixture applies to every test automatically.
    The monkeypatch is reverted at teardown by pytest.
    """
    # Obtain the underlying connection that test_db_session is bound to.
    # In SQLAlchemy 2.x, Session.get_bind() returns the connection/engine.
    # We use the connection directly so all sessions share the same transaction.
    connection = test_db_session.get_bind()

    # Create a sessionmaker for UoW sessions: same connection, separate identity maps,
    # expire_on_commit=False so ORM attributes survive after the session is closed.
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

            # Monkey-patch the session's commit to also expire test_db_session
            # objects, ensuring test assertions and subsequent requests see
            # data changed by this UoW's transaction.
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
    from backend.shared.rate_limiter import limiter

    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    # Override get_uow so any endpoint using Depends(get_uow) resolves to
    # the same SQLite test session — NOT to a real Postgres connection.
    # NOTE: NO uow.close() here — lifecycle is managed by the test_db_session
    # fixture (session.close() + transaction.rollback() at teardown). Closing
    # twice would break tests that query test_db_session directly after a request.
    def override_get_uow():
        uow = UnitOfWork(test_db_session)
        try:
            yield uow
        except Exception:
            uow.rollback()
            raise

    app.dependency_overrides[get_uow] = override_get_uow

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
    from backend.features.catalog.models import Rol

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
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

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
    """Get authentication headers for the sample user."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "test_password_123",
        },
    )
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}
