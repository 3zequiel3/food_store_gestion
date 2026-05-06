"""
Pytest configuration and fixtures for Food Store backend.

Provides fixtures for:
- Test database session
- Test FastAPI client
- Test user and data factories
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.database import Base, get_db


# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)


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


@pytest.fixture(scope="function")
def client(test_db_session: Session) -> TestClient:
    """Create a test client with dependency override."""

    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

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
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "test_password_123",
        },
    )
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}
