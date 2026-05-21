"""
RFC 7807 Problem Details error handlers for FastAPI.

All exceptions are caught and formatted into a consistent JSON structure:
{
    "type": "about:blank",
    "title": "Not Found",
    "status": 404,
    "detail": "Product with id 999 not found",
    "instance": "/api/products/999"
}

Validation errors include an "errors" array with per-field details.
"""

import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    request_validation_exception_handler as _pydantic_handler,
)

from shared.exceptions import (
    FoodStoreError,
    NotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
    BusinessRuleError,
    ConflictError,
    UpstreamError,
)

logger = logging.getLogger(__name__)


def _problem_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build an RFC 7807 Problem Details JSON response."""
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _problem_response(404, "Not Found", exc.detail, str(request.url.path))


async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return _problem_response(403, "Forbidden", exc.detail, str(request.url.path))


async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return _problem_response(401, "Unauthorized", exc.detail, str(request.url.path))


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _problem_response(409, "Conflict", exc.detail, str(request.url.path))


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    extra: dict[str, Any] = {}
    if exc.field:
        extra["errors"] = [{"field": exc.field, "message": exc.detail}]
    return _problem_response(422, "Validation Error", "Invalid input data", str(request.url.path), extra)


async def upstream_error_handler(request: Request, exc: UpstreamError) -> JSONResponse:
    """Map UpstreamError (e.g. mp_unreachable) to HTTP 502 Bad Gateway with Problem Details."""
    return _problem_response(
        502,
        "Bad Gateway",
        exc.detail,
        str(request.url.path),
        {"code": exc.code},
    )


async def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
    # 409 for state-machine / business-rule conflicts, 422 otherwise
    status = 409 if "conflict" in exc.code.lower() or "state" in exc.code.lower() else 422
    title = "Conflict" if status == 409 else "Validation Error"
    return _problem_response(status, title, exc.detail, str(request.url.path))


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic v2 validation errors to RFC 7807 with per-field details."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg", "Invalid value")})

    return _problem_response(
        422,
        "Validation Error",
        "Invalid input data",
        str(request.url.path),
        {"errors": errors},
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException in RFC 7807 format.

    This catches Starlette's 404/405 exceptions (starlette.exceptions.HTTPException)
    as well as manually raised FastAPI HTTPException from user code.
    FastAPI's HTTPException is a subclass of Starlette's HTTPException.
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: PLC0415

    if not isinstance(exc, StarletteHTTPException):
        raise exc  # pragma: no cover — should never happen

    # Map common HTTP status codes to RFC 7807 titles
    status_titles = {
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
    }
    title = status_titles.get(exc.status_code, "HTTP Error")
    extra: dict[str, Any] = {}
    if isinstance(exc.detail, dict):
        detail = str(exc.detail.get("detail") or exc.detail.get("message") or title)
        for key in ("code", "mp_status", "status_detail", "raw_cause"):
            if key in exc.detail:
                extra[key] = exc.detail[key]
    else:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return _problem_response(
        exc.status_code,
        title,
        detail,
        str(request.url.path),
        extra or None,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors. NEVER expose stack traces to clients."""
    logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
    return _problem_response(
        500,
        "Internal Server Error",
        "An unexpected error occurred. Please try again later.",
        str(request.url.path),
    )