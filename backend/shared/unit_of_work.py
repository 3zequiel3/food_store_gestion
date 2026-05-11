"""
Unit of Work pattern for transaction management.

Coordinates multiple repositories within a single transaction boundary.
"""

import logging
from typing import Any, Dict

from backend.shared.database import get_session_factory
from backend.shared.repository import BaseRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.

    Manages multiple repositories and ensures atomic operations
    across multiple tables (e.g., creating order + payment in one transaction).

    Standard usage (context manager — service-owned lifecycle):
        with UnitOfWork() as uow:
            uow.register_repository("orders", OrderRepository(uow.session))
            order = uow.orders.create(user_id=user_id, total=100)
            # __exit__ commits on clean exit, rolls back on exception, closes session

    In tests, get_session_factory is monkeypatched by the conftest so that
    UnitOfWork() automatically uses the in-memory SQLite session.
    """

    def __init__(self) -> None:
        """
        Initialize UnitOfWork.

        Creates its own session via get_session_factory(). In tests,
        get_session_factory is monkeypatched to return a factory that creates
        sessions bound to the test SQLite connection.
        """
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
        Can be used for intermediate commits (e.g. flush before bulk operation).
        Normally the __exit__ on context manager exit handles the final commit.
        """
        try:
            self.session.commit()
            logger.debug("UnitOfWork committed successfully")
        except Exception as e:
            self.session.rollback()
            logger.error(f"UnitOfWork commit failed: {str(e)}")
            raise

    def rollback(self) -> None:
        """
        Rollback the transaction.

        All changes made through registered repositories are discarded.
        """
        try:
            self.session.rollback()
            logger.debug("UnitOfWork rolled back")
        except Exception as e:
            logger.error(f"UnitOfWork rollback failed: {str(e)}")
            raise

    def close(self) -> None:
        """Close the session."""
        try:
            self.session.close()
            logger.debug("UnitOfWork session closed")
        except Exception as e:
            logger.error(f"Failed to close UnitOfWork session: {str(e)}")
            raise
