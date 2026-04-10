"""
Users feature router.

Endpoints for user management.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_users():
    """
    List all users.

    Implementation in users feature.
    """
    return {"status": "not_implemented"}


@router.get("/{user_id}")
async def get_user(user_id: str):
    """
    Get user by ID.

    Implementation in users feature.
    """
    return {"status": "not_implemented"}


@router.post("/")
async def create_user():
    """
    Create new user.

    Implementation in users feature.
    """
    return {"status": "not_implemented"}
