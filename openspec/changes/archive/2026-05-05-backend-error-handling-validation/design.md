# Design: backend-error-handling-validation

## Arquitectura

### Flujo de errores

```
Request → Router (validación Pydantic automática → 422)
        → Service (lanza custom exception)
        → Exception Handler global (formatea a RFC 7807)
        → Response JSON
```

### Capas involucradas

1. **Pydantic v2** → Rechaza inputs inválidos automáticamente con 422
2. **Custom Exceptions** → Clases específicas por tipo de error
3. **Exception Handler Global** → FastAPI `exception_handler` que formatea todo a RFC 7807
4. **Sanitización** → Limpieza de strings en schemas Pydantic

## Custom Exceptions

Archivo: `backend/shared/exceptions.py`

```python
class FoodStoreError(Exception):
    """Base exception for all domain errors."""
    def __init__(self, detail: str, code: str = "food_store_error"):
        self.detail = detail
        self.code = code
        super().__init__(detail)

class NotFoundError(FoodStoreError):
    """Resource not found — maps to HTTP 404."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, code="not_found")

class ForbiddenError(FoodStoreError):
    """Insufficient permissions — maps to HTTP 403."""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(detail, code="forbidden")

class UnauthorizedError(FoodStoreError):
    """Authentication required or invalid — maps to HTTP 401."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(detail, code="unauthorized")

class ValidationError(FoodStoreError):
    """Business rule validation failed — maps to HTTP 422."""
    def __init__(self, detail: str, field: str | None = None):
        super().__init__(detail, code="validation_error")
        self.field = field

class BusinessRuleError(FoodStoreError):
    """Business rule violated — maps to HTTP 409 (Conflict) or 422."""
    def __init__(self, detail: str, code: str = "business_rule_error"):
        super().__init__(detail, code=code)

class ConflictError(FoodStoreError):
    """Resource conflict (e.g., duplicate unique field) — maps to HTTP 409."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(detail, code="conflict")
```

## RFC 7807 Response Format

Todos los errores devuelven:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Product with id 999 not found",
  "instance": "/api/products/999"
}
```

Para errores de validación con detalle por campo:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "Invalid input data",
  "instance": "/api/auth/login",
  "errors": [
    { "field": "email", "message": "Invalid email format" },
    { "field": "password", "message": "Password must be at least 8 characters" }
  ]
}
```

## Exception Handlers en FastAPI

Archivo: `backend/shared/error_handler.py`

Se registran handlers en `main.py`:

| Excepción | HTTP Status | Manejador |
|-----------|-------------|-----------|
| `NotFoundError` | 404 | `not_found_handler` |
| `ForbiddenError` | 403 | `forbidden_handler` |
| `UnauthorizedError` | 401 | `unauthorized_handler` |
| `ValidationError` | 422 | `validation_error_handler` |
| `BusinessRuleError` | 422/409 | `business_rule_handler` |
| `ConflictError` | 409 | `conflict_handler` |
| `RequestValidationError` (Pydantic) | 422 | `request_validation_handler` |
| `HTTPException` (FastAPI) | Variable | `http_exception_handler` |
| `Exception` (genérica) | 500 | `generic_handler` |

## Sanitización de Inputs

### En schemas Pydantic (por campo)

```python
from pydantic import field_validator
import html

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def sanitize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def sanitize_password(cls, v: str) -> str:
        return v.strip()
```

### Reglas de sanitización

| Tipo | Regla | Ejemplo |
|------|-------|---------|
| Email | `strip()` + `lower()` | `"  Test@Email.COM  "` → `"test@email.com"` |
| String nombre/texto | `strip()` + max length + HTML escape | `"  Juan  "` → `"Juan"` |
| Password | `strip()` (no escapar, puede tener caracteres especiales) | |
| Teléfono | `strip()` + validar dígitos | |
| Números | Rechazar strings no numéricos (Pydantic lo hace automático) | |

### SQL Injection

- SQLModel/SQLAlchemy usa **query parameterization** automáticamente
- Nunca se concatena SQL manualmente
- No se necesita sanitización adicional para campos que van al ORM

### XSS en backend

- El backend **no renderiza HTML**, el XSS es problema del frontend
- El backend sanitiza para prevenir datos corruptos en la BD
- Para campos como nombre/descripción: `html.escape()` como capa extra de defensa

## Plan de Tests

### Unit tests (`backend/tests/test_error_handling.py`)

| Test | Qué verifica |
|------|-------------|
| `test_not_found_error_returns_rfc7807` | `NotFoundError` → 404 con formato RFC 7807 |
| `test_forbidden_error_returns_rfc7807` | `ForbiddenError` → 403 con formato RFC 7807 |
| `test_unauthorized_error_returns_rfc7807` | `UnauthorizedError` → 401 con formato RFC 7807 |
| `test_validation_error_returns_rfc7807` | `ValidationError` → 422 con detalle por campo |
| `test_conflict_error_returns_rfc7807` | `ConflictError` → 409 con formato RFC 7807 |
| `test_generic_exception_returns_500_sanitized` | `Exception` → 500 sin stack trace expuesto |
| `test_pydantic_validation_error_returns_422` | Input inválido a endpoint → 422 con detalle de campo |
| `test_email_sanitization` | Email con espacios/mayúsculas → sanitizado |
| `test_string_sanitization_strips_whitespace` | String con espacios → strip |

### Integration tests (en `test_main.py`)

| Test | Qué verifica |
|------|-------------|
| `test_health_check_unchanged` | El health check sigue funcionando |
| `test_not_found_route_returns_404` | Ruta inexistente → 404 limpio |

## Modificaciones a archivos existentes

### `backend/main.py`

- **Eliminar** el `generic_exception_handler` actual (líneas 130-137)
- **Agregar** import de `backend.shared.error_handler`
- **Registrar** todos los exception handlers del módulo

### `backend/tests/conftest.py`

- **Ya arreglado** como pre-requisito (import de `Usuario`, `Producto`, `Rol`)

## No se modifica

- Modelos ORM
- Routers (se mantienen como placeholders hasta sus respectivos changes)
- Services (se mantienen vacíos hasta sus respectivos changes)
- Frontend (este change es 100% backend)
