"""
Auth feature router.

Endpoints for authentication and user session management.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    """
    Login endpoint.

    Implementation in auth feature.
    """
    return {"status": "not_implemented"}


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    Implementation in auth feature.
    """
    return {"status": "not_implemented"}
