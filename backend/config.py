"""
Application configuration using Pydantic v2 BaseSettings.

Reads from .env file during development and environment variables in production.
"""

import os
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:2005@localhost:5432/FoodStoreDB",
        description="PostgreSQL database connection URL",
    )

    # Security
    JWT_SECRET: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT token signing",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT signing (HS256 or RS256)",
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )

    # Auth cookies (development defaults; production Secure=true is follow-up)
    AUTH_COOKIE_ACCESS_NAME: str = Field(default="access_token")
    AUTH_COOKIE_REFRESH_NAME: str = Field(default="refresh_token")
    AUTH_COOKIE_ACCESS_PATH: str = Field(default="/api/v1")
    AUTH_COOKIE_REFRESH_PATH: str = Field(default="/api/v1/auth")
    AUTH_COOKIE_SAMESITE: str = Field(default="lax")
    AUTH_COOKIE_SECURE: bool = Field(default=False)

    # Server
    API_PORT: int = Field(default=8000, description="API server port")
    ENVIRONMENT: str = Field(
        default="development", description="Environment (development/production)"
    )
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # MercadoPago
    MP_ACCESS_TOKEN: str = Field(
        default="TEST-your-mp-access-token-here",
        description="MercadoPago access token (use TEST- prefix for sandbox)",
    )

    # File storage
    STORAGE: str = Field(
        default="local",
        description="Storage backend for uploads: local or s3",
    )
    STORAGE_LOCAL_DIR: str = Field(
        default=str(Path(__file__).parent / "uploads"),
        description="Local upload directory. Defaults to backend/uploads",
    )
    STORAGE_PUBLIC_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public base URL used for local upload URLs",
    )
    STORAGE_MAX_UPLOAD_MB: int = Field(default=5, description="Max upload size in MB")
    S3_ENDPOINT_URL: str | None = Field(default=None)
    S3_REGION: str = Field(default="auto")
    S3_BUCKET_NAME: str | None = Field(default=None)
    S3_ACCESS_KEY_ID: str | None = Field(default=None)
    S3_SECRET_ACCESS_KEY: str | None = Field(default=None)
    S3_PUBLIC_BASE_URL: str | None = Field(
        default=None,
        description="Optional public CDN/base URL for S3 object URLs",
    )

    # AWS-compatible names (Railway default injection)
    # These are mapped to S3_* fields if S3_* are not explicitly set.
    AWS_ENDPOINT_URL: str | None = Field(default=None, exclude=True)
    AWS_S3_BUCKET_NAME: str | None = Field(default=None, exclude=True)
    AWS_DEFAULT_REGION: str | None = Field(default=None, exclude=True)
    AWS_ACCESS_KEY_ID: str | None = Field(default=None, exclude=True)
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None, exclude=True)

    def model_post_init(self, _context) -> None:
        """Map AWS_* env vars to S3_* fields if S3_* are not explicitly set."""
        if not self.S3_ENDPOINT_URL and self.AWS_ENDPOINT_URL:
            object.__setattr__(self, "S3_ENDPOINT_URL", self.AWS_ENDPOINT_URL)
        if not self.S3_BUCKET_NAME and self.AWS_S3_BUCKET_NAME:
            object.__setattr__(self, "S3_BUCKET_NAME", self.AWS_S3_BUCKET_NAME)
        if self.S3_REGION == "auto" and self.AWS_DEFAULT_REGION:
            object.__setattr__(self, "S3_REGION", self.AWS_DEFAULT_REGION)
        if not self.S3_ACCESS_KEY_ID and self.AWS_ACCESS_KEY_ID:
            object.__setattr__(self, "S3_ACCESS_KEY_ID", self.AWS_ACCESS_KEY_ID)
        if not self.S3_SECRET_ACCESS_KEY and self.AWS_SECRET_ACCESS_KEY:
            object.__setattr__(self, "S3_SECRET_ACCESS_KEY", self.AWS_SECRET_ACCESS_KEY)

    # CORS
    FRONTEND_URL: str = Field(
        default="http://localhost:5173", description="Frontend application URL for CORS"
    )

    class Config:
        """Pydantic config."""

        env_file = str(Path(__file__).parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = (
            "ignore"  # Tolerate unrelated env vars (e.g. shell exports like DB_USER)
        )

    @field_validator("STORAGE", mode="before")
    @classmethod
    def validate_storage(cls, v):
        value = str(v or "local").lower()
        if value not in {"local", "s3"}:
            raise ValueError("STORAGE must be 'local' or 's3'")
        return value

    @field_validator("AUTH_COOKIE_SECURE", mode="before")
    @classmethod
    def validate_cookie_secure(cls, v):
        if (
            str(v).lower() in ("false", "0")
            and os.getenv("ENVIRONMENT") == "production"
        ):
            raise ValueError("AUTH_COOKIE_SECURE must be true in production!")
        return v

    @field_validator("JWT_SECRET", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Ensure JWT_SECRET is not empty."""
        if not v or v == "your-super-secret-key-change-in-production":
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError(
                    "JWT_SECRET must be set and not the default value in production!"
                )
            # In development, allow the default value with a warning
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "⚠️  JWT_SECRET is using default value - change this in production!"
            )
        return v

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Get CORS allowed origins."""
        origins = [
            "http://localhost:5173",  # Vite dev server (default)
            "http://localhost:3000",  # Alternative React dev server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
        # Add frontend URL from config
        if self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)

        # Add production URLs if in production
        if self.ENVIRONMENT == "production" and "localhost" not in self.FRONTEND_URL:
            origins = [self.FRONTEND_URL]

        return origins


# Global settings instance
settings = Settings()
