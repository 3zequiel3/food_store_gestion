# Change: backend-error-handling-validation

## ¿Qué?

Implementar el manejo de errores estandarizado en RFC 7807 (Problem Details for HTTP APIs) y la validación/sanitización de inputs en todo el backend.

## ¿Por qué?

1. **RN-DA08**: La regla de negocio exige que todos los errores sigan RFC 7807.
2. **US-068 + US-074**: El frontend necesita un formato de error consistente para mostrar mensajes al usuario.
3. **Seguridad**: Sin sanitización, los inputs son vulnerables a inyecciones y datos corruptos.
4. **Cuello de botella**: Todo módulo futuro (auth, productos, pedidos) necesita este patrón antes de escribir sus routers. Sin esto, cada módulo manejaría errores a su manera.

## Historias cubiertas

- US-068: Manejo de errores estandarizado en backend
- US-074: Validación y sanitización de inputs

## Impacto

- Se modifica `backend/main.py` (reemplazar el exception handler genérico actual)
- Se crea `backend/shared/exceptions.py` (custom exceptions)
- Se crea `backend/shared/error_handler.py` (middleware RFC 7807)
- Se actualiza `conftest.py` y `tests/` (ya arreglado como pre-requisito)
- Los routers placeholder existentes devolverán errores en formato correcto

## No incluye

- Lógica de negocio de ningún módulo (auth, productos, etc.)
- Validación específica de reglas de negocio (FSM, stock, etc.)
- TanStack Query ni frontend
