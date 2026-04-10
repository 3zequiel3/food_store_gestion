"""
Products feature router.

Endpoints for product management.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_products():
    """
    List all products.

    Implementation in products feature.
    """
    return {"status": "not_implemented"}


@router.get("/{product_id}")
async def get_product(product_id: str):
    """
    Get product by ID.

    Implementation in products feature.
    """
    return {"status": "not_implemented"}


@router.post("/")
async def create_product():
    """
    Create new product.

    Implementation in products feature.
    """
    return {"status": "not_implemented"}
