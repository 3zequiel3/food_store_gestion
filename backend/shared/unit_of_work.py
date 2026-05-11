"""
Unit of Work pattern for transaction management.

Coordinates multiple repositories within a single transaction boundary.
"""

import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from backend.shared.database import get_session_factory
from backend.shared.repository import BaseRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.

    Manages multiple repositories and ensures atomic operations
    across multiple tables (e.g., creating order + payment in one transaction).

    Preferred usage (context manager — service-owned lifecycle):
        with UnitOfWork() as uow:
            uow.register_repository("orders", OrderRepository(uow.session))
            order = uow.orders.create(user_id=user_id, total=100)
            # __exit__ commits on clean exit, rolls back on exception

    Legacy usage (external session injection — backward-compat):
        uow = UnitOfWork(session)
        ...
        uow.commit()
    """

    def __init__(self, session_or_factory: Any = None) -> None:
        """
        Initialize UnitOfWork.

        Args:
            session_or_factory: One of:
                - Session instance (legacy backward-compat mode) → session not owned.
                - None (default) → calls get_session_factory()() and owns the session.
        """
        if isinstance(session_or_factory, Session):
            # Legacy mode: external session injected directly — UoW does NOT own it.
            # This path is used by the legacy get_uow() dependency (Step 1 backward-compat)
            # and test overrides that inject the session directly.
            self.session: Session = session_or_factory
            self._owns_session = False
        else:
            # Default: call the module-level factory to get a session factory,
            # then call that to create a session. UoW owns and closes the session.
            # In tests, get_session_factory is monkeypatched to return a factory
            # that creates sessions bound to the test connection.
            factory = get_session_factory()
            self.session = factory()
            self._owns_session = True
        self._repositories: Dict[str, BaseRepository] = {}

    # ── Context manager protocol ──────────────────────────────────────────

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        try:
            if exc_type is None:
                self.session.commit()
                logger.debug("UnitOfWork committed successfully")
            else:
                self.session.rollback()
                logger.debug("UnitOfWork rolled back due to exception")
        finally:
            if self._owns_session:
                self.close()
        return False  # do not suppress exceptions

    def register_repository(
        self,
        name: str,
        repository: BaseRepository,
    ) -> None:
        """
        Register a repository with this UnitOfWork.

        Args:
            name: Repository name (e.g., 'users', 'orders')
            repository: Repository instance
        """
        self._repositories[name] = repository

    def __getattr__(self, name: str) -> BaseRepository:
        """
        Get a registered repository by name.

        Args:
            name: Repository name

        Returns:
            Repository instance

        Raises:
            AttributeError: If repository not registered
        """
        if name.startswith("_"):
            return super().__getattribute__(name)

        if name in self._repositories:
            return self._repositories[name]

        raise AttributeError(f"Repository '{name}' not registered in UnitOfWork")

    def commit(self) -> None:
        """
        Commit the transaction.

        All changes made through registered repositories are persisted.
        """
        try:
            self.session.commit()
            logger.debug("✅ UnitOfWork committed successfully")
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ UnitOfWork commit failed: {str(e)}")
            raise

    def rollback(self) -> None:
        """
        Rollback the transaction.

        All changes made through registered repositories are discarded.
        """
        try:
            self.session.rollback()
            logger.debug("↩️  UnitOfWork rolled back")
        except Exception as e:
            logger.error(f"❌ UnitOfWork rollback failed: {str(e)}")
            raise

    def close(self) -> None:
        """Close the session."""
        try:
            self.session.close()
            logger.debug("🔒 UnitOfWork session closed")
        except Exception as e:
            logger.error(f"❌ Failed to close UnitOfWork session: {str(e)}")
            raise
