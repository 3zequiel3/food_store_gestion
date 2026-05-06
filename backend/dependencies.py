"""
Dependency injection setup for FastAPI.

Provides factories for common dependencies like UnitOfWork and current user.

NOTE: Database session dependency (`get_db`) is defined in `backend.shared.database`.
Use `from backend.shared.database import get_db` in feature routers.
This module exposes only higher-level dependencies (UoW, current user).
"""

import logging
from typing import Generator

from backend.shared.database import get_session_factory
from backend.shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def get_uow() -> Generator[UnitOfWork, None, None]:
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
    session = get_session_factory()()
    uow = UnitOfWork(session)
    try:
        logger.debug("UnitOfWork created")
        yield uow
    except Exception as e:
        logger.error(f"UnitOfWork error: {str(e)}")
        uow.rollback()
        raise
    finally:
        uow.close()


async def get_current_user():
    """
    Dependency: Get current user from JWT token.

    Placeholder — real implementation is in backend.features.auth.dependencies.

    Usage in router:
        @router.get("/profile")
        def get_profile(current_user = Depends(get_current_user)):
            return current_user

    Returns:
        Current user object

    Raises:
        UnauthorizedError: If not authenticated
    """
    # TODO: Wire to backend.features.auth.dependencies.get_current_user
    return None
