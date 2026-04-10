"""
Unit of Work pattern for transaction management.

Coordinates multiple repositories within a single transaction boundary.
"""

import logging
from typing import Dict, Optional, Type

from sqlalchemy.orm import Session

from backend.shared.repository import BaseRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.

    Manages multiple repositories and ensures atomic operations
    across multiple tables (e.g., creating order + payment in one transaction).

    Usage:
        uow = UnitOfWork(session)
        try:
            order = uow.orders.create(user_id=user_id, total=100)
            payment = uow.payments.create(order_id=order.id, amount=100)
            uow.commit()
        except Exception:
            uow.rollback()
            raise
    """

    def __init__(self, session: Session):
        """
        Initialize UnitOfWork.

        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self._repositories: Dict[str, BaseRepository] = {}

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
