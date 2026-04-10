"""
Application configuration using Pydantic v2 BaseSettings.

Reads from .env file during development and environment variables in production.
"""

import os
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://food_user:food_password@localhost:5432/food_store",
        description="PostgreSQL database connection URL",
    )

    # Security
    JWT_SECRET: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT token signing",
    )

    # Server
    API_PORT: int = Field(default=8000, description="API server port")
    ENVIRONMENT: str = Field(
        default="development", description="Environment (development/production)"
    )
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # CORS
    FRONTEND_URL: str = Field(
        default="http://localhost:5173", description="Frontend application URL for CORS"
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

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
