## Why

El backend de autenticación (JWT + refresh tokens + RBAC) está completo y archivado (`auth-backend`). Las cuatro stores de Zustand —incluyendo `useAuthStore` con `login()`, `logout()`, `updateTokens()` y soporte para `getState()` fuera de React— también están archivadas (`zustand-stores-base`). Sin embargo, ningún flujo de autenticación existe en el frontend: no hay formularios de login/registro, el interceptor de Axios está scaffoldeado pero sin lógica real de JWT, y no hay capa de servicio que conecte el frontend con los endpoints `/api/v1/auth/*`. Este change cierra esa brecha y deja al usuario capaz de autenticarse end-to-end.

## What Changes

- **Nuevo**: Servicio `authService` con funciones tipadas para `register`, `login`, `refresh` y `logout` contra los endpoints `/api/v1/auth/*`.
- **Nuevo**: Formulario de registro (`RegisterForm`) con validación client-side: email, contraseña ≥ 8 caracteres, nombre y apellido ≥ 2 caracteres.
- **Nuevo**: Formulario de login (`LoginForm`) con validación client-side y manejo de error 401 (credenciales inválidas) y 429 (rate limiting).
- **Nuevo**: Páginas `/login` y `/register` que consumen los formularios y orquestan el flujo via `authService` + `useAuthStore`.
- **Implementado**: Interceptor de request de Axios que adjunta `Authorization: Bearer <token>` desde `useAuthStore.getState().accessToken`.
- **Implementado**: Interceptor de response de Axios que, ante un 401, ejecuta refresh con singleton lock y cola de requests pendientes (US-066), y redirige a `/login` si el refresh falla.
- **Implementado**: Handler global de errores HTTP que traduce respuestas RFC 7807 a toasts via `useUIStore.pushToast()` (US-067).

## Capabilities

### New Capabilities

- `auth-forms`: Formularios de login y registro con validación, manejo de errores de la API (401, 409, 422, 429) y feedback visual vía toast.
- `auth-service`: Capa de acceso a la API de autenticación — funciones tipadas `register`, `login`, `refresh`, `logout` que consumen los endpoints del backend y mapean las respuestas a los tipos del dominio frontend.

### Modified Capabilities

- `http-client`: Completar la implementación de los interceptores de Axios — el interceptor de request debe adjuntar el JWT desde `useAuthStore`, y el interceptor de response debe implementar el patrón singleton-refresh + queue de requests para manejar 401 de forma concurrente sin múltiples llamadas a refresh simultáneas.

## Impact

- **Frontend** (`frontend/`): Nuevas páginas y componentes en la feature `auth/`. Extensión del módulo `http-client` con lógica de interceptores concreta.
- **Stores**: `useAuthStore` (login/logout/updateTokens), `useUIStore` (pushToast) — no se modifica su API, solo se consume.
- **Dependencias nuevas**: `react-hook-form`, `zod` (o `@hookform/resolvers/zod`) para validación de formularios.
- **Rutas**: Se añaden `/login` y `/register` como rutas públicas (sin guard). Las rutas protegidas quedan pendientes para `navigation-routing-base`.
- **No hay cambios en el backend**.
