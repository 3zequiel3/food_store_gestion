"""
Pytest configuration and fixtures for Food Store backend.

Provides fixtures for:
- Test database session
- Test FastAPI client
- Test user and data factories
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.models import Base
from backend.dependencies import get_db_session


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

    def override_get_db_session():
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_user(test_db_session: Session):
    """Create a sample user for testing."""
    from backend.features.users.models import User
    from backend.shared.enums import Role

    user = User(
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        is_active=True,
        role=Role.USER,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def sample_product(test_db_session: Session):
    """Create a sample product for testing."""
    from backend.features.products.models import Product

    product = Product(
        name="Test Product",
        description="A test product",
        price=99.99,
        is_active=True,
    )
    test_db_session.add(product)
    test_db_session.commit()
    test_db_session.refresh(product)

    return product
