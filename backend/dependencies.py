"""
Dependency injection setup for FastAPI.

NOTE: get_db() was removed in refactor-auth-to-uow. The session dependency
pattern has been fully replaced:
- Business operations: use UnitOfWork() from shared.unit_of_work
  (each service method owns the transaction boundary via `with UnitOfWork()`).
- Read-only middleware (e.g. get_current_user): use get_session_factory()()
  from shared.unit_of_work with a try/finally close block.

NOTE: get_uow was removed in refactor-uow-to-context-manager. UnitOfWork
lifecycle is now managed by service methods via `with UnitOfWork() as uow:`.
Routers no longer receive UnitOfWork via FastAPI dependency injection.
"""

import logging

logger = logging.getLogger(__name__)
