## Context

El scaffold del frontend (`setup-frontend-core`) dejó listos: las cuatro stores Zustand, el router con `PublicRoute`/`PrivateRoute`/`RoleRoute`, y un `apiClient` Axios con interceptor de request (adjunta JWT) y un interceptor de response **stub** que ante 401 simplemente hace logout + redirect. Las páginas `/login` y `/register` existen como HTML estático sin lógica.

Este change completa la capa de autenticación frontend: implementa el interceptor de response con refresh real, crea el servicio de auth, y conecta los formularios.

## Goals / Non-Goals

**Goals:**
- Interceptor de response con patrón singleton-refresh + cola de requests (US-066).
- `authService`: capa de API tipada para `register`, `login`, `refresh`, `logout`.
- `LoginForm` y `RegisterForm` funcionales con validación Zod + react-hook-form.
- Handler global RFC 7807 → toast via `useUIStore.pushToast`.
- Sin cambios en el router ni en las guards de rutas (eso es `navigation-routing-base`).

**Non-Goals:**
- Página de perfil de usuario (change #13, `user-profile`).
- Guards de rutas basadas en rol (change #8, `navigation-routing-base`).
- Persistencia del refresh token en httpOnly cookie (fuera de alcance de la spec).
- Tests unitarios de los formularios con testing-library (pueden agregarse en un change de testing dedicado).

## Decisions

### D1: Singleton lock para el refresh (vs. múltiples llamadas simultáneas)

**Decisión**: Una variable de módulo `isRefreshing: boolean` + array `pendingQueue: Array<{resolve, reject}>` en `client.ts`. Cuando el interceptor detecta un 401 y `isRefreshing == false`, activa el lock, llama a `/api/v1/auth/refresh`, y al terminar resuelve o rechaza toda la cola. Las requests que llegan mientras `isRefreshing == true` se encolan en vez de llamar a refresh ellas mismas.

**Alternativa descartada**: Usar un `Subject` de RxJS o un observable — overkill, introduce una dependencia nueva sin beneficio real para un queue sencillo.

**Por qué**: Es el patrón canónico para este problema, sin dependencias extra. Está documentado como requisito en US-066 ("Si hay múltiples requests concurrentes y el token expira, se encolan las requests y se resuelven todas tras el refresh").

### D2: authService como módulo de funciones (vs. clase / hook)

**Decisión**: Funciones exportadas directamente (`register`, `login`, `refresh`, `logout`) en `src/features/auth/api/authService.ts`. No es una clase ni un custom hook.

**Por qué**: El interceptor de Axios llama a `refresh` fuera de React — necesita una función estándar importable, no un hook. Las páginas de login/registro tampoco necesitan abstracción de clase. Mantiene la consistencia con el patrón ya usado en el proyecto (funciones de store actions directas).

### D3: react-hook-form + Zod (vs. validación manual)

**Decisión**: Instalar `react-hook-form` + `zod` + `@hookform/resolvers/zod` para los formularios.

**Por qué**: Es el stack definido en `docs/Descripcion.txt` para el proyecto. Zod permite compartir el schema de validación entre el frontend y cualquier test, y genera mensajes de error tipados. La alternativa (HTML5 validation + estado manual) es frágil y verbosa.

**Dependencias nuevas**: `react-hook-form ^7`, `zod ^3`, `@hookform/resolvers ^3`.

### D4: Manejo de errores RFC 7807 → toast

**Decisión**: Función `handleApiError(error: AxiosError)` en `src/shared/api/errorHandler.ts`. La función parsea el body RFC 7807 (`detail`, `errors[]`) y llama a `useUIStore.getState().pushToast(...)`. Se invoca al final del interceptor de response (después del bloque de refresh).

**Por qué**: `useUIStore.getState()` funciona fuera de React igual que `useAuthStore.getState()`. Centralizar el manejo de errores en el interceptor evita que cada componente tenga que manejar errores de red manualmente.

### D5: Estructura de archivos en `features/auth/`

```
src/features/auth/
├── api/
│   ├── authService.ts      ← register, login, refresh, logout
│   └── types.ts            ← LoginRequest, RegisterRequest, TokenPairResponse, UserResponse
└── ui/
    ├── LoginForm.tsx
    └── RegisterForm.tsx
```

Las páginas (`LoginPage`, `RegisterPage`) ya existen en `src/pages/` y solo importan los componentes de `features/auth/ui/`.

## Risks / Trade-offs

- **[Risk] Token en localStorage es vulnerable a XSS** → El proyecto optó por este enfoque desde `zustand-stores-base`. La mitigación correcta (httpOnly cookie) requeriría cambios en el backend (Set-Cookie) y está fuera de alcance de esta spec.
- **[Risk] El refresh token viaja en el body** → Consistente con el contrato del backend (`POST /api/v1/auth/refresh` acepta `{ refresh_token: string }` en body). No hay httpOnly cookie en esta versión.
- **[Trade-off] Validación solo en frontend** → Los errores 422 del backend (validación Pydantic) también se muestran via toast. El usuario ve doble feedback (Zod antes de enviar + toast del backend si algo pasa). Aceptable y común.
- **[Risk] Race condition en el queue durante el refresh** → Si el refresh falla (401 o error de red), todas las requests en cola se rechazan con ese error. Cada componente debe manejar ese rechazo. El interceptor no hace retry infinito — un solo intento de refresh, y si falla, logout.

## Migration Plan

1. Instalar dependencias: `pnpm add react-hook-form zod @hookform/resolvers` en `frontend/`.
2. Crear `src/features/auth/api/types.ts` con los tipos del contrato de auth.
3. Crear `src/features/auth/api/authService.ts`.
4. Crear `src/shared/api/errorHandler.ts`.
5. Reemplazar el interceptor stub en `src/shared/api/client.ts` con el interceptor completo.
6. Crear `src/features/auth/ui/LoginForm.tsx` y `RegisterForm.tsx`.
7. Reemplazar el HTML estático de `LoginPage.tsx` y `RegisterPage.tsx` con los componentes nuevos.
8. Exportar desde los index files correspondientes.

No hay rollback complejo — si algo falla, el interceptor stub original se puede restaurar sin efecto en otras partes del sistema.

## Open Questions

- **Toast de rate limiting (429)**: ¿Mostrar el tiempo de `Retry-After` header o un mensaje genérico? Por defecto se usará mensaje genérico; si el backend incluye el header, el interceptor puede parsearlo.
- **Redirect post-login**: ¿Volver a la URL anterior o siempre ir a `/`? Por ahora siempre a `/` — la lógica de "redirect a la URL de origen" pertenece a `navigation-routing-base`.
