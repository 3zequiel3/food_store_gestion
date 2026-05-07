## 1. Dependencias y tipos

- [x] 1.1 Instalar dependencias: `pnpm add react-hook-form zod @hookform/resolvers` en `frontend/`
- [x] 1.2 Crear `src/features/auth/api/types.ts` con `RegisterRequest`, `LoginRequest`, `TokenPair`, `AuthSuccessResponse`, `UsuarioProfile`
- [x] 1.3 Asegurar que `src/features/auth/` tiene `api/` y `ui/` con sus `index.ts` (crear la estructura si no existe)

## 2. Auth Service

- [x] 2.1 Crear `src/features/auth/api/authService.ts` con función `register(data: RegisterRequest): Promise<AuthSuccessResponse>` — POST `/api/v1/auth/register`, mapper de `roles[].codigo` a `string[]`
- [x] 2.2 Agregar función `login(data: LoginRequest): Promise<AuthSuccessResponse>` — POST `/api/v1/auth/login`
- [x] 2.3 Agregar función `refresh(refreshToken: string): Promise<TokenPair>` — POST `/api/v1/auth/refresh` usando `axios` directo (NO `apiClient`)
- [x] 2.4 Agregar función `logout(refreshToken: string): Promise<void>` — POST `/api/v1/auth/logout`, silenciar errores (best-effort)
- [x] 2.5 Exportar `authService` y tipos desde `src/features/auth/api/index.ts`

## 3. Error Handler Global

- [x] 3.1 Crear `src/shared/api/errorHandler.ts` con `handleApiError(error: AxiosError): void` que extrae el campo `detail` o `errors[0].message` del body RFC 7807
- [x] 3.2 La función llama a `useUIStore.getState().pushToast({ id: crypto.randomUUID(), message, level: 'error' })`
- [x] 3.3 Excluir explícitamente errores 401 (no deben generar toast)
- [x] 3.4 Manejar el caso sin `response` (error de red) con mensaje genérico "Error de conexión, revisá tu red"
- [x] 3.5 Exportar `handleApiError` desde `src/shared/api/index.ts`

## 4. Interceptor de Axios (singleton refresh + queue)

- [x] 4.1 En `src/shared/api/client.ts`, declarar las variables de módulo `let isRefreshing = false` y `let pendingQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []`
- [x] 4.2 Implementar la función helper `flushQueue(token: string | null, error: unknown)` que resuelve o rechaza todos los items de `pendingQueue` y la vacía
- [x] 4.3 Reemplazar el interceptor de response stub con la lógica completa: detectar `error.response?.status === 401`, comprobar `isRefreshing`, encolar si está activo, o activar el lock y llamar `authService.refresh`
- [x] 4.4 En el callback de refresh exitoso: llamar `useAuthStore.getState().updateTokens(newTokens)`, `flushQueue(newToken, null)`, resetear `isRefreshing = false`, y reintentar la request original con el nuevo token
- [x] 4.5 En el callback de refresh fallido: llamar `useAuthStore.getState().logout()`, `flushQueue(null, refreshError)`, resetear `isRefreshing = false`, y redirigir a `/login`
- [x] 4.6 Al final del interceptor (errores que no son 401), llamar `handleApiError(error)` antes de hacer `Promise.reject(error)`

## 5. LoginForm

- [x] 5.1 Crear `src/features/auth/ui/LoginForm.tsx` con schema Zod: `email` (z.string().email()) y `password` (z.string().min(1))`
- [x] 5.2 Implementar el submit handler: llamar `authService.login`, en éxito `useAuthStore.getState().login(tokens, user)` + navegar a `/` con `useNavigate`
- [x] 5.3 Manejar error 401: mostrar mensaje "Credenciales inválidas" inline (state local, no toast)
- [x] 5.4 Manejar error 429: llamar `useUIStore.getState().pushToast` con mensaje de rate limiting
- [x] 5.5 Deshabilitar el botón de submit y mostrar indicador de carga mientras `isSubmitting` es `true`
- [x] 5.6 Mostrar errores de validación Zod inline debajo de cada campo

## 6. RegisterForm

- [x] 6.1 Crear `src/features/auth/ui/RegisterForm.tsx` con schema Zod: `nombre` (min 2, max 80), `apellido` (min 2, max 80), `email` (email), `password` (min 8)
- [x] 6.2 Implementar el submit handler: llamar `authService.register`, en éxito `useAuthStore.getState().login(tokens, user)` + navegar a `/`
- [x] 6.3 Manejar error 409: mostrar mensaje "Este email ya está registrado" inline junto al campo email
- [x] 6.4 Deshabilitar el botón de submit y mostrar indicador de carga mientras `isSubmitting` es `true`
- [x] 6.5 Mostrar errores de validación Zod inline debajo de cada campo
- [x] 6.6 Exportar `LoginForm` y `RegisterForm` desde `src/features/auth/ui/index.ts`

## 7. Páginas

- [x] 7.1 Reemplazar el HTML estático de `src/pages/login/LoginPage.tsx` para que renderice `<LoginForm />` (mantener el contenedor visual existente)
- [x] 7.2 Reemplazar el HTML estático de `src/pages/register/RegisterPage.tsx` para que renderice `<RegisterForm />` (mantener el contenedor visual existente)
- [x] 7.3 Verificar que `src/features/index.ts` exporta el módulo `auth`

## 8. Verificación

- [x] 8.1 Verificar con TypeScript (`pnpm tsc --noEmit`) que no hay errores de tipos
- [x] 8.2 Smoke test manual: navegar a `/login`, ingresar credenciales válidas, verificar que `useAuthStore` tiene el token y el usuario, verificar redirección a `/`
- [x] 8.3 Smoke test manual: navegar a `/register`, crear cuenta nueva, verificar login automático post-registro
- [x] 8.4 Smoke test del interceptor: con el devtools, invalidar manualmente el token en localStorage, hacer una request autenticada, verificar que el refresh ocurre y la request se reintenta
