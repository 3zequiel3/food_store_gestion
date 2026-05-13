"""
Base service class with business logic layer.
"""

import logging
from typing import Generic, Optional, TypeVar

from shared.repository import BaseRepository
from sqlalchemy.orm import Session

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseService(Generic[T]):
    """
    Base service for business logic.

    Services coordinate repositories and implement business rules.
    Always use UnitOfWork for transaction management.
    """

    def __init__(self, repository: BaseRepository[T]):
        """
        Initialize service.

        Args:
            repository: Repository instance for data access
        """
        self.repository = repository

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """
        Get all entities.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        return self.repository.list(skip=skip, limit=limit)

    def get_by_id(self, id) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        return self.repository.read(id)

    def create(self, **kwargs) -> T:
        """
        Create new entity.

        Args:
            **kwargs: Entity fields

        Returns:
            Created entity
        """
        return self.repository.create(**kwargs)

    def update(self, id, **kwargs) -> Optional[T]:
        """
        Update entity.

        Args:
            id: Entity ID
            **kwargs: Fields to update

        Returns:
            Updated entity or None if not found
        """
        return self.repository.update(id, **kwargs)

    def delete(self, id) -> bool:
        """
        Delete entity (soft delete).

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(id)
