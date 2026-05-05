# Tasks: backend-error-handling-validation

> **Regla**: Marcar `[x]` cada task al completarla. No saltar tasks.

## Pre-requisitos

- [x] `conftest.py` corregido (imports de `Usuario`, `Producto`, `Rol`, `Base` de `database.py`)
- [x] `test_main.py` verifica que routes placeholder existen

## 1. Custom Exceptions

- [x] Crear `backend/shared/exceptions.py` con:
  - `FoodStoreError` (base) con `detail` y `code`
  - `NotFoundError` (→ 404)
  - `ForbiddenError` (→ 403)
  - `UnauthorizedError` (→ 401)
  - `ValidationError` (→ 422, con `field` opcional)
  - `BusinessRuleError` (→ 409/422)
  - `ConflictError` (→ 409)

## 2. Exception Handlers RFC 7807

- [x] Crear `backend/shared/error_handler.py` con handlers para:
  - `NotFoundError` → `{"type","title","status","detail","instance"}`
  - `ForbiddenError` → RFC 7807 con status 403
  - `UnauthorizedError` → RFC 7807 con status 401
  - `ValidationError` → RFC 7807 con array `errors` por campo
  - `ConflictError` → RFC 7807 con status 409
  - `BusinessRuleError` → RFC 7807 con status apropiado
  - `RequestValidationError` (Pydantic) → RFC 7807 con detalle de campos
  - `HTTPException` → RFC 7807
  - `Exception` (genérica) → 500 sanitizado (sin stack trace)

## 3. Registrar handlers en main.py

- [x] Eliminar el `generic_exception_handler` actual de `main.py` (líneas 130-137)
- [x] Importar `error_handler` desde `backend.shared.error_handler`
- [x] Registrar todos los exception handlers con `app.exception_handler()`

## 4. Sanitización de Inputs

- [x] Crear función de sanitización reutilizable en `backend/shared/sanitizers.py`:
  - `sanitize_string(v: str) -> str` (strip + HTML escape)
  - `sanitize_email(v: str) -> str` (strip + lower)
  - `sanitize_phone(v: str) -> str` (solo dígitos, +, -, (), espacios)
- [x] Verificar `backend/shared/__init__.py` — ya existe, no necesita cambios

## 5. Tests

- [x] Crear `backend/tests/test_error_handling.py` con tests:
  - `test_response_has_required_fields`
  - `test_not_found_error_returns_404_rfc7807`
  - `test_generic_exception_returns_500_sanitized`
  - `test_email_sanitization_strips_and_lowercases`
  - `test_string_sanitization_strips_and_escapes_html`
  - `test_phone_sanitization_removes_invalid_chars`
  - `test_health_check_returns_ok`
- [x] Agregar test de sanitización:
  - `test_email_sanitization_strips_and_lowercases`
  - `test_string_sanitization_strips_whitespace`
- [x] Verificar que `test_main.py` sigue pasando (health check, CORS, 404)
- [x] Correr `pytest backend/tests/ -v` → TODO verde (14/14 passed)

## 6. Spec Delta

- [x] Crear `openspec/changes/backend-error-handling-validation/specs/error-handling/spec.md` con:
  - Requirements para RFC 7807 format
  - Requirements para custom exceptions
  - Requirements para sanitización de inputs

## 7. Verificación Final

- [x] `pytest backend/tests/ -v --tb=short` → 100% pass (14/14)
- [x] Revisar que ningún error expone stack trace en response
- [x] Verificar que `GET /health` sigue funcionando igual
- [x] Verificar que los placeholders de routers devuelven respuesta (aunque sea `not_implemented`) sin romper el formato de error
