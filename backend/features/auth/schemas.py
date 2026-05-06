"""
Auth feature Pydantic schemas.

Request/response DTOs for authentication endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (min 8 characters)",
        examples=["securePassword123"],
    )
    nombre: str = Field(
        ...,
        min_length=2,
        max_length=80,  # Per spec §6.1 (was 100)
        description="User's first name",
        examples=["Juan"],
    )
    apellido: str = Field(
        ...,
        min_length=2,
        max_length=80,  # Per spec §6.1 (was 100)
        description="User's last name",
        examples=["Perez"],
    )


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="User's password",
        examples=["securePassword123"],
    )


class TokenPairResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    refresh_token: str = Field(
        ...,
        description="Opaque refresh token (valid for 7 days)",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        examples=[1800],
    )


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str = Field(
        ...,
        description="The refresh token to exchange for new tokens",
    )


class TokenPayload(BaseModel):
    """Decoded JWT payload structure."""

    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    roles: list[str] = Field(default=[], description="User roles")
    exp: int = Field(..., description="Expiration timestamp")
    type: str = Field(default="access", description="Token type")


class UserResponse(BaseModel):
    """Response schema for authenticated user info (GET /me)."""

    id: int = Field(..., description="User ID")
    nombre: str = Field(..., description="First name")
    apellido: str = Field(..., description="Last name")
    email: EmailStr = Field(..., description="Email address")
    roles: list[str] = Field(..., description="Role codes")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}
