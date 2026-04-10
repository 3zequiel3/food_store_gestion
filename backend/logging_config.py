"""
Logging configuration for the Food Store backend.

Sets up structured logging with timestamps, log levels, and module context.
"""

import logging
import logging.config
from backend.config import settings


def setup_logging():
    """Configure logging with structured format."""

    # Define log format
    log_format = "[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": date_format,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Root logger
            "": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": True,
            },
            # FastAPI/Starlette loggers
            "fastapi": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            # SQLAlchemy logger
            "sqlalchemy": {
                "handlers": ["console"],
                "level": "WARNING",  # Only warn about SQLAlchemy issues
                "propagate": False,
            },
            # Backend loggers
            "backend": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)

    logger = logging.getLogger(__name__)
    logger.info(f"✅ Logging initialized at {settings.LOG_LEVEL} level")


# Slow query/endpoint threshold logging
SLOW_QUERY_THRESHOLD_MS = 1000
SLOW_ENDPOINT_THRESHOLD_MS = 5000


def log_slow_query(duration_ms: float, query: str):
    """Log a slow database query."""
    logger = logging.getLogger("backend.database")
    if duration_ms > SLOW_QUERY_THRESHOLD_MS:
        logger.warning(f"⚠️  SLOW QUERY ({duration_ms:.2f}ms): {query[:100]}...")


def log_slow_endpoint(duration_ms: float, method: str, path: str):
    """Log a slow API endpoint."""
    logger = logging.getLogger("backend.http")
    if duration_ms > SLOW_ENDPOINT_THRESHOLD_MS:
        logger.warning(f"⚠️  SLOW ENDPOINT ({duration_ms:.2f}ms): {method} {path}")
