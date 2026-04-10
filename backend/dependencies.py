"""
Dependency injection setup for FastAPI.

Provides factories for common dependencies like database session,
UnitOfWork, and current user context.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings
from backend.shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


# Database engine and session factory
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",  # Log SQL if debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connection before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency: Get database session.

    Usage in router:
        @router.get("/")
        def my_endpoint(session: Session = Depends(get_db_session)):
            ...

    Yields:
        SQLAlchemy session
    """
    session = SessionLocal()
    try:
        logger.debug("📊 Database session opened")
        yield session
    except Exception as e:
        logger.error(f"❌ Database session error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("🔒 Database session closed")


def get_uow(session: Session = None) -> Generator[UnitOfWork, None, None]:
    """
    Dependency: Get UnitOfWork instance.

    Usage in router:
        @router.post("/")
        def my_endpoint(uow: UnitOfWork = Depends(get_uow)):
            try:
                # Use repositories through uow
                uow.users.create(...)
                uow.orders.create(...)
                uow.commit()
            except Exception:
                uow.rollback()
                raise

    Yields:
        UnitOfWork instance
    """
    if session is None:
        session = SessionLocal()

    uow = UnitOfWork(session)
    try:
        logger.debug("🔄 UnitOfWork created")
        yield uow
    except Exception as e:
        logger.error(f"❌ UnitOfWork error: {str(e)}")
        uow.rollback()
        raise
    finally:
        uow.close()


async def get_current_user():
    """
    Dependency: Get current user from JWT token.

    Placeholder - implemented in auth feature.

    Usage in router:
        @router.get("/profile")
        def get_profile(current_user = Depends(get_current_user)):
            return current_user

    Returns:
        Current user object

    Raises:
        HTTPException: If not authenticated
    """
    # TODO: Extract and validate JWT token
    # TODO: Return user from database
    return None
