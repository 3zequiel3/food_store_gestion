"""
FastAPI application entry point for Food Store

This module initializes the FastAPI application with all middleware,
CORS configuration, and feature routers.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from logging_config import setup_logging
from shared.rate_limiter import limiter
from shared.exceptions import (
    NotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ConflictError,
    ValidationError,
    BusinessRuleError,
    UpstreamError,
)
from shared.error_handler import (
    not_found_handler,
    forbidden_handler,
    unauthorized_handler,
    conflict_handler,
    validation_error_handler,
    business_rule_handler,
    upstream_error_handler,
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
from features.users import models as _user_models  # noqa: F401
from features.catalog import models as _catalog_models  # noqa: F401
from features.products import models as _product_models  # noqa: F401
from features.orders import models as _order_models  # noqa: F401
from features.payments import models as _payment_models  # noqa: F401
from features.addresses import models as _address_models  # noqa: F401
from features.auth import models as _auth_models  # noqa: F401


# Feature routers
from features.auth.router import router as auth_router
from features.users.router import router as users_router
from features.products.router import router as products_router
from features.orders.router import router as orders_router
from features.payments.router import router as payments_router
from features.addresses.router import router as addresses_router
from features.categories.router import router as categories_router
from features.ingredients.router import router as ingredients_router
from features.catalog.router import router as catalog_router
from features.admin_users.router import router as admin_users_router
from features.admin_metrics.router import router as admin_metrics_router
from features.checkout.router import router as checkout_router
from features.cocina.router import router as cocina_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("🚀 Food Store backend starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")

    from shared.database import Base, get_engine
    from scripts.seed import run_seed

    engine = get_engine()

    # En development local, crear el schema directo desde los models para
    # iterar rápido sin migraciones. En testing/production Alembic se encarga
    # del schema (ver Procfile: bootstrap → upgrade head → uvicorn).
    if settings.ENVIRONMENT == "development":
        Base.metadata.create_all(bind=engine)
        logger.info("Schema sincronizado con Base.metadata.create_all (development)")

    run_seed()

    # Start KDS WebSocket event drain task (D5, Slice 3)
    try:
        loop = asyncio.get_running_loop()
        from features.cocina.service import start_drain_task
        start_drain_task(loop)
    except RuntimeError:
        # No running event loop during startup — will be started when first request comes
        pass

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
app.add_exception_handler(UpstreamError, upstream_error_handler)  # 502 for MP/upstream failures
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

# Serve local uploads when STORAGE=local. In S3 mode this directory is unused,
# but mounting it is harmless and keeps local development URLs stable.
Path(settings.STORAGE_LOCAL_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.STORAGE_LOCAL_DIR), name="uploads")


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
app.include_router(users_router, prefix="/api/v1/usuarios", tags=["users"])
app.include_router(products_router, prefix="/api/v1/productos", tags=["products"])
app.include_router(orders_router, prefix="/api/v1/pedidos", tags=["orders"])
app.include_router(payments_router, prefix="/api/v1/pagos", tags=["payments"])
app.include_router(checkout_router, prefix="/api/v1/checkout", tags=["checkout"])
app.include_router(addresses_router, prefix="/api/v1/direcciones", tags=["addresses"])
app.include_router(categories_router, prefix="/api/v1/categorias", tags=["categories"])
app.include_router(
    ingredients_router, prefix="/api/v1/ingredientes", tags=["ingredients"]
)
app.include_router(catalog_router, prefix="/api/v1", tags=["catalog"])
app.include_router(
    admin_users_router, prefix="/api/v1/admin/usuarios", tags=["admin-users"]
)
app.include_router(
    admin_metrics_router, prefix="/api/v1/admin/metricas", tags=["admin-metrics"]
)
app.include_router(cocina_router, prefix="/api/v1/cocina", tags=["cocina"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
