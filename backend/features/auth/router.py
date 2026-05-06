"""
Auth feature router.

Authentication endpoints with rate limiting protection.
All error responses follow RFC 7807 Problem Details format.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from backend.features.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
)
from backend.features.auth.service import AuthService
from backend.shared.database import get_db
from backend.shared.exceptions import UnauthorizedError
from backend.shared.rate_limiter import RATE_LIMITS, limiter

router = APIRouter()

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.post(
    "/register",
    response_model=TokenPairResponse,
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account with CLIENT role automatically assigned.",
)
@limiter.limit(RATE_LIMITS["register"])
async def register(
    request: Request,
    data: RegisterRequest,
    db=Depends(get_db),
):
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **password**: Minimum 8 characters
    - **nombre**: First name (2-100 characters)
    - **apellido**: Last name (2-100 characters)

    Returns a token pair (access + refresh) on success.
    Rate limit: 3 registrations per hour per IP.
    """
    service = AuthService(db)
    user = await service.register(data)
    return await service._create_token_pair(user)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="User login",
    description="Authenticate with email and password to receive access and refresh tokens.",
)
@limiter.limit(RATE_LIMITS["login"])
async def login(
    request: Request,
    data: LoginRequest,
    db=Depends(get_db),
):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: Account password

    Returns a token pair on success.
    Rate limit: 5 attempts per 15 minutes per IP.
    Error message is the same for invalid email or password (security).
    """
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    return await service.login(data, client_ip=client_ip)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Refresh access token",
    description="Exchange a refresh token for a new token pair. Implements token rotation.",
)
@limiter.limit(RATE_LIMITS["refresh"])
async def refresh(
    request: Request,
    data: RefreshRequest,
    db=Depends(get_db),
):
    """
    Refresh tokens using a refresh token.

    - **refresh_token**: Valid refresh token received from login/register

    Returns a new token pair. The old refresh token is marked as used.
    Rate limit: 10 requests per minute per IP.
    """
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    status_code=204,
    summary="User logout",
    description="Revoke the refresh token to end the session.",
)
async def logout(
    data: RefreshRequest,
    db=Depends(get_db),
):
    """
    Logout and revoke refresh token.

    - **refresh_token**: The refresh token to revoke

    Returns 204 No Content on success.
    Note: Access tokens remain valid until expiration (stateless).
    """
    service = AuthService(db)
    await service.logout(data.refresh_token)
    return None


@router.get(
    "/me",
    summary="Get current user info",
    description="Returns information about the authenticated user.",
)
async def get_me(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
):
    """
    Get current authenticated user information.

    Requires a valid access token in the Authorization header.
    """
    from backend.features.auth.dependencies import get_current_user
    user = await get_current_user(token, db)
    return {
        "id": user.id,
        "email": user.email,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "roles": [rol.codigo for rol in user.roles],
    }
