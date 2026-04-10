"""
Orders feature router.

Endpoints for order management.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_orders():
    """
    List all orders.

    Implementation in orders feature.
    """
    return {"status": "not_implemented"}


@router.get("/{order_id}")
async def get_order(order_id: str):
    """
    Get order by ID.

    Implementation in orders feature.
    """
    return {"status": "not_implemented"}


@router.post("/")
async def create_order():
    """
    Create new order.

    Implementation in orders feature.
    """
    return {"status": "not_implemented"}
