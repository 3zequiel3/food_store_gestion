"""
Pydantic v2 schemas for Category CRUD.

Four schemas cover the full API surface:
- CategoriaCreate: input for POST /
- CategoriaUpdate: input for PUT /{id}
- CategoriaRead: output for POST and PUT
- CategoriaTreeNode: output for GET / (recursive tree)

Plus CategoryFlatRow: internal dataclass for CTE result rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


# ── Internal types ────────────────────────────────────────────────────────


@dataclass
class CategoryFlatRow:
    """Flat row returned by the recursive CTE before Python-side nesting.

    This is an internal type used by CategoryRepository.get_tree_cte() and
    CategoryService.get_tree(). It is NOT exposed over the API.
    """

    id: int
    nombre: str
    padre_id: int | None
    depth: int


# ── Request schemas ───────────────────────────────────────────────────────


class CategoriaCreate(BaseModel):
    """Payload for creating a new category."""

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Bebidas"],
    )
    padre_id: int | None = Field(
        None,
        description="ID of the parent category. Null = root category.",
        examples=[None],
    )


class CategoriaUpdate(BaseModel):
    """Payload for updating an existing category.

    All fields are optional. The service uses ``model_dump(exclude_unset=True)``
    to distinguish between "not sent" and "explicitly set to null", which is
    critical for ``padre_id``:
    - ``{"nombre": "X"}`` → keep current parent.
    - ``{"nombre": "X", "padre_id": null}`` → promote to root.
    """

    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        examples=["Bebidas Sin Alcohol"],
    )
    padre_id: int | None = Field(
        None,
        description="ID of the new parent category. Null = promote to root.",
        examples=[1],
    )


# ── Response schemas ──────────────────────────────────────────────────────


class CategoriaRead(BaseModel):
    """Public representation of a single category (non-recursive)."""

    id: int
    nombre: str
    padre_id: int | None
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class CategoriaTreeNode(BaseModel):
    """Recursive tree node for the public GET / endpoint.

    ``subcategorias`` is populated by the service after the CTE query.
    The forward reference requires ``model_rebuild()`` at module end.
    """

    id: int
    nombre: str
    padre_id: int | None
    subcategorias: list[CategoriaTreeNode] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# Resolve the forward reference in CategoriaTreeNode
CategoriaTreeNode.model_rebuild()
