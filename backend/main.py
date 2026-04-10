"""
FastAPI application entry point for Food Store backend.

This module initializes the FastAPI application with all middleware,
CORS configuration, and feature routers.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import setup_logging


# Configure logging on startup
setup_logging()
logger = logging.getLogger(__name__)


# Feature routers
from backend.features.auth.router import router as auth_router
from backend.features.users.router import router as users_router
from backend.features.products.router import router as products_router
from backend.features.orders.router import router as orders_router
from backend.features.payments.router import router as payments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("🚀 Food Store backend starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    yield
    # Shutdown
    logger.info("🛑 Food Store backend shutting down...")


# Create FastAPI app instance
app = FastAPI(
    title="Food Store API",
    description="Backend API for Food Store application",
    version="1.0.0",
    lifespan=lifespan,
)


# Configure CORS
allowed_origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_request_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """Log all HTTP requests with method, path, status, and duration."""
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(
            f"Unhandled exception in {request.method} {request.url.path}", exc_info=exc
        )
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[ERROR] {request.method} {request.url.path} → 500 Internal Server Error ({duration_ms:.2f}ms)"
        )
        raise

    duration_ms = (time.time() - start_time) * 1000
    status_text = "OK" if response.status_code < 400 else "ERROR"

    # Log request with color-coded status
    if response.status_code < 300:
        level = logging.INFO
    elif response.status_code < 400:
        level = logging.INFO
    elif response.status_code < 500:
        level = logging.WARNING
    else:
        level = logging.ERROR

    logger.log(
        level,
        f"{request.method} {request.url.path} → {response.status_code} {status_text} ({duration_ms:.2f}ms)",
    )

    # Warn if slow
    if duration_ms > 5000:  # 5 second threshold for endpoints
        logger.warning(
            f"⚠️  SLOW ENDPOINT: {request.method} {request.url.path} took {duration_ms:.2f}ms"
        )

    return response


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


# Register feature routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
app.include_router(payments_router, prefix="/api/payments", tags=["payments"])


# Global exception handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions globally."""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_server_error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
