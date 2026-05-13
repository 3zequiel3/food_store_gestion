"""
Auth feature router.

Authentication endpoints with rate limiting protection.
All error responses follow RFC 7807 Problem Details format.

Router does NOT receive any Session or UnitOfWork via dependency injection.
Transaction ownership lives in AuthService — each service method opens
its own UnitOfWork context.
"""

from fastapi import APIRouter, Depends, Request, Response

from config import settings
from features.auth.cookies import clear_auth_cookies, set_auth_cookies
from features.auth.dependencies import get_current_user
from features.auth.schemas import (
    AuthSessionResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from features.auth.service import AuthService
from features.users.models import Usuario
from shared.exceptions import UnauthorizedError
from shared.rate_limiter import RATE_LIMITS, limiter

router = APIRouter()


def _session_response(tokens) -> AuthSessionResponse:
    """Project the internal token response to the public cookie-session DTO."""
    return AuthSessionResponse(
        user=tokens.user,
        expires_in=tokens.expires_in,
        token_type="cookie",
    )


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account with CLIENT role automatically assigned.",
)
@limiter.limit(RATE_LIMITS["register"])
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
):
    """Register a new user and start a cookie-backed session."""
    service = AuthService()
    tokens = service.register(data)
    set_auth_cookies(response, tokens)
    return _session_response(tokens)


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="User login",
    description="Authenticate with email and password and set HttpOnly auth cookies.",
)
@limiter.limit(RATE_LIMITS["login"])
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
):
    """Login with email and password and start a cookie-backed session."""
    service = AuthService()
    client_ip = request.client.host if request.client else None
    tokens = service.login(data, client_ip=client_ip)
    set_auth_cookies(response, tokens)
    return _session_response(tokens)


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    summary="Refresh access token",
    description="Rotate refresh token from HttpOnly cookie and set new auth cookies.",
)
@limiter.limit(RATE_LIMITS["refresh"])
async def refresh(
    request: Request,
    response: Response,
):
    """Refresh tokens using the refresh token HttpOnly cookie."""
    refresh_token = request.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)
    if not refresh_token:
        raise UnauthorizedError("Token de refresco requerido")

    service = AuthService()
    tokens = service.refresh(refresh_token)
    set_auth_cookies(response, tokens)
    return _session_response(tokens)


@router.post(
    "/logout",
    status_code=204,
    summary="User logout",
    description="Revoke refresh token cookie and clear auth cookies.",
)
async def logout(
    request: Request,
    response: Response,
):
    """Best-effort logout: revoke if refresh cookie exists, always clear cookies."""
    refresh_token = request.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)
    if refresh_token:
        service = AuthService()
        service.logout(refresh_token)

    clear_auth_cookies(response)
    return None


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
    description="Returns information about the authenticated user.",
)
async def get_me(
    user: Usuario = Depends(get_current_user),
):
    """Get current authenticated user information from auth cookies."""
    return UserResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        roles=[rol.codigo for rol in user.roles],
        created_at=user.creado_en,
    )
