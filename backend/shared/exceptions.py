"""
Custom domain exceptions for Food Store backend.

All exceptions map to HTTP status codes and are handled by the
global error handler to produce RFC 7807 Problem Details responses.
"""


class FoodStoreError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, detail: str, code: str = "food_store_error") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


class NotFoundError(FoodStoreError):
    """Resource not found — maps to HTTP 404."""

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail, code="not_found")


class ForbiddenError(FoodStoreError):
    """Insufficient permissions — maps to HTTP 403."""

    def __init__(self, detail: str = "Access forbidden") -> None:
        super().__init__(detail, code="forbidden")


class UnauthorizedError(FoodStoreError):
    """Authentication required or invalid — maps to HTTP 401."""

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(detail, code="unauthorized")


class ValidationError(FoodStoreError):
    """Business rule validation failed — maps to HTTP 422."""

    def __init__(self, detail: str, field: str | None = None) -> None:
        super().__init__(detail, code="validation_error")
        self.field = field


class BusinessRuleError(FoodStoreError):
    """Business rule violated — maps to HTTP 422 or 409."""

    def __init__(self, detail: str, code: str = "business_rule_error") -> None:
        super().__init__(detail, code=code)


class ConflictError(FoodStoreError):
    """Resource conflict (e.g., duplicate unique field) — maps to HTTP 409."""

    def __init__(self, detail: str = "Resource conflict") -> None:
        super().__init__(detail, code="conflict")