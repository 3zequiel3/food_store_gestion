"""
Base repository class with CRUD operations.

Provides standard data access patterns for all repositories.
Includes soft delete support (queries exclude eliminado_en IS NOT NULL by default).
"""

import logging
from typing import Any, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

T = TypeVar("T")
logger = logging.getLogger(__name__)

# ID type can be int (BIGSERIAL) or UUID
IDType = Union[int, UUID]


class BaseRepository(Generic[T]):
    """
    Base repository for data access.

    Provides CRUD operations: create, read, update, delete, list.
    Supports soft delete (eliminado_en field).
    """

    def __init__(self, session: Session, model: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
        self._has_eliminado_en = hasattr(model, "eliminado_en")

    def _get_base_query(self):
        """
        Get base query with soft delete filter applied.

        Returns queries that exclude soft-deleted records by default.
        """
        query = select(self.model)
        if self._has_eliminado_en:
            query = query.where(self.model.eliminado_en.is_(None))
        return query

    def create(self, **kwargs) -> T:
        """
        Create and save a new entity.

        Args:
            **kwargs: Field values for the new entity

        Returns:
            Created entity instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        logger.debug(f"Created {self.model.__name__}: {instance.id}")
        return instance

    def read(self, id: IDType) -> Optional[T]:
        """
        Read an entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        query = self._get_base_query().where(self.model.id == id)
        instance = self.session.execute(query).scalar_one_or_none()
        logger.debug(f"Read {self.model.__name__}: {id}")
        return instance

    def update(self, id: IDType, **kwargs) -> Optional[T]:
        """
        Update an entity.

        Args:
            id: Entity ID
            **kwargs: Fields to update

        Returns:
            Updated entity instance or None if not found
        """
        instance = self.read(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key) and key not in ("id", "creado_en"):
                setattr(instance, key, value)

        self.session.flush()
        logger.debug(f"Updated {self.model.__name__}: {id}")
        return instance

    def delete(self, id: IDType) -> bool:
        """
        Soft delete an entity (sets eliminado_en timestamp).

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        instance = self.read(id)
        if not instance:
            return False

        if self._has_eliminado_en:
            from datetime import datetime, timezone

            instance.eliminado_en = datetime.now(timezone.utc)
            self.session.flush()
            logger.debug(f"Soft deleted {self.model.__name__}: {id}")
        else:
            # Hard delete if model doesn't support soft delete
            self.session.delete(instance)
            self.session.flush()
            logger.debug(f"Hard deleted {self.model.__name__}: {id}")

        return True

    def hard_delete(self, id: IDType) -> bool:
        """
        Permanently delete an entity (hard delete).

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        # Bypass soft delete filter
        query = select(self.model).where(self.model.id == id)
        instance = self.session.execute(query).scalar_one_or_none()
        if not instance:
            return False

        self.session.delete(instance)
        self.session.flush()
        logger.debug(f"Hard deleted {self.model.__name__}: {id}")
        return True

    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        List entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        query = self._get_base_query().offset(skip).limit(limit)
        instances = self.session.execute(query).scalars().all()
        logger.debug(f"Listed {self.model.__name__}: {len(instances)} records")
        return instances

    def count(self) -> int:
        """
        Count non-deleted entities.

        Returns:
            Total count
        """
        from sqlalchemy import func

        query = select(func.count(self.model.id))
        if self._has_eliminado_en:
            query = query.where(self.model.eliminado_en.is_(None))
        count = self.session.execute(query).scalar() or 0
        return count
