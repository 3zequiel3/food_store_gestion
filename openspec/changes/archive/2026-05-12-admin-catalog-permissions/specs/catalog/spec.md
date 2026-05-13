## MODIFIED Requirements

### RN-CA10: Parámetro `incluir_eliminados` para ADMIN

**Requirement**: Los endpoints de listado de catálogo (`GET /api/v1/productos`, `GET /api/v1/ingredientes`) DEBEN aceptar el query param `incluir_eliminados: bool` (default `False`). Cuando `True` y el solicitante tiene rol ADMIN, el resultado incluye registros con `eliminado_en IS NOT NULL`. Para cualquier otro rol o sin autenticación, el param es ignorado y solo se retornan registros activos.

**Base spec**: RN-CA10 de `docs/Historias_de_usuario.txt`.

### US-064: Admin tiene acceso completo a gestión de catálogo

**Requirement**: Todos los endpoints de escritura de productos, categorías e ingredientes (POST, PUT, DELETE, PATCH) DEBEN aceptar rol ADMIN además de STOCK. Los guards son `require_role("ADMIN", "STOCK")`. Esta es la especificación canónica — el comportamiento ya está implementado y este spec lo formaliza.

### US-065: Admin tiene acceso completo a gestión de pedidos

**Requirement**: Los endpoints de lectura y transición de pedidos (`GET /api/v1/pedidos`, `GET /api/v1/pedidos/{id}`, `PATCH /api/v1/pedidos/{id}/estado`) DEBEN aceptar rol ADMIN con el mismo acceso que PEDIDOS (vista completa, sin anti-leak 404). La función `_is_admin_view()` en `OrderService` es el punto de verificación canónico.
