"""
Dependency injection setup for FastAPI.

NOTE: Database session dependency (`get_db`) is defined in `backend.shared.database`.
Use `from backend.shared.database import get_db` in feature routers.

NOTE: `get_uow` was removed in refactor-uow-to-context-manager. UnitOfWork lifecycle
is now managed by service methods via `with UnitOfWork() as uow:`. Routers no longer
receive UnitOfWork via FastAPI dependency injection.
"""

import logging

logger = logging.getLogger(__name__)


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
