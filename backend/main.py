"""
FastAPI application entry point for Food Store backend.

This module initializes the FastAPI application with all middleware,
CORS configuration, and feature routers.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.logging_config import setup_logging
from backend.shared.rate_limiter import limiter
from backend.shared.exceptions import (
    NotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ConflictError,
    ValidationError,
    BusinessRuleError,
)
from backend.shared.error_handler import (
    not_found_handler,
    forbidden_handler,
    unauthorized_handler,
    conflict_handler,
    validation_error_handler,
    business_rule_handler,
    request_validation_handler,
    http_exception_handler,
    generic_exception_handler,
)


# Configure logging on startup
setup_logging()
logger = logging.getLogger(__name__)


# Register all SQLAlchemy models in the metadata BEFORE the app handles
# any request. SQLAlchemy resolves string-based relationship targets
# (e.g. relationship("Pedido")) lazily, but every referenced class must
# already exist in the registry by the time the first mapper configures.
# Without these imports, queries against any model that has cross-feature
# relationships (Usuario -> Pedido, Usuario -> DireccionEntrega, etc.)
# fail at runtime with InvalidRequestError.
from backend.features.users import models as _user_models  # noqa: F401
from backend.features.catalog import models as _catalog_models  # noqa: F401
from backend.features.products import models as _product_models  # noqa: F401
from backend.features.orders import models as _order_models  # noqa: F401
from backend.features.payments import models as _payment_models  # noqa: F401
from backend.features.addresses import models as _address_models  # noqa: F401
from backend.features.auth import models as _auth_models  # noqa: F401


# Feature routers
from backend.features.auth.router import router as auth_router
from backend.features.users.router import router as users_router
from backend.features.products.router import router as products_router
from backend.features.orders.router import router as orders_router
from backend.features.payments.router import router as payments_router
from backend.features.categories.router import router as categories_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("🚀 Food Store backend starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")

    from backend.shared.database import Base, get_engine
    from backend.scripts.seed import run_seed

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    run_seed()

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

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register RFC 7807 exception handlers (D5) — order: specific → generic
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(ForbiddenError, forbidden_handler)
app.add_exception_handler(UnauthorizedError, unauthorized_handler)
app.add_exception_handler(ConflictError, conflict_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(BusinessRuleError, business_rule_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
# HTTPException covers both manually raised FastAPI HTTPException AND
# Starlette's automatic 404/405 responses. Using the class reference here
# (not an integer status code) ensures ALL HTTPException subclasses are caught.
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Starlette 404 for unknown routes also comes through as HTTPException,
# but some Starlette versions route it before add_exception_handler picks it up.
# Override the default handler explicitly to ensure RFC 7807 for 404/405.
from starlette.exceptions import HTTPException as StarletteHTTPException
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


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


# Register feature routers — all under /api/v1/ per spec §5 (Integrador.txt)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(products_router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(payments_router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(categories_router, prefix="/api/v1/categorias", tags=["categories"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
