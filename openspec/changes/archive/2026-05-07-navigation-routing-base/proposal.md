## Why

El flujo de autenticación está completo (`auth-frontend-interceptor`), pero el frontend carece de navegación funcional: la `Navbar` muestra los mismos links para todos los roles, el logout no invalida el refresh token en el backend, el `LoginForm` ignora la URL original al redirigir post-login, y no existe ningún componente que renderice los toasts que `handleApiError` ya enqueue en `useUIStore`. Este change completa el esqueleto de navegación: router con todas las rutas guardadas por rol, navbar adaptada por rol (US-075), redirects correctos y toast UI visible.

## What Changes

- **Modificado**: `Navbar.tsx` — menú adaptado por rol según US-075: CLIENT ve catálogo/carrito/pedidos/perfil/direcciones; STOCK ve productos/categorías/ingredientes; PEDIDOS ve panel de pedidos; ADMIN ve todo + usuarios + métricas. Sin autenticación solo se ve catálogo.
- **Modificado**: `Navbar.tsx` — logout llama `authService.logout(refreshToken)` para invalidar el refresh token en el backend antes de limpiar el estado local.
- **Modificado**: `LoginForm.tsx` — al hacer login exitoso, redirige a `location.state?.from` si existe, o a `/` como fallback.
- **Modificado**: `AppLayout.tsx` — agrega `<ToastContainer />` para renderizar los toasts de `useUIStore`.
- **Nuevo**: `ToastContainer.tsx` — componente que lee `useUIStore.toasts` y renderiza notificaciones con auto-dismiss.
- **Modificado**: `Router.tsx` — registrar todas las rutas de la aplicación con sus guards correctos (PrivateRoute + RoleRoute), incluso como placeholders. Las páginas reales llegan en changes posteriores.

## Capabilities

### New Capabilities

- `navigation`: Navbar con menús diferenciados por rol (CLIENT / STOCK / PEDIDOS / ADMIN / público), toggle de tema, botones de auth, y logout con invalidación de token en backend.
- `toast-ui`: Componente `ToastContainer` que renderiza el array `toasts` de `useUIStore` con auto-dismiss configurable y botón de cierre manual.

### Modified Capabilities

- `routing-guards`: Extender el router con el conjunto completo de rutas de la aplicación, cada una con el guard correcto (pública / PrivateRoute / RoleRoute). Agregar redirect post-login a la URL de origen.

## Impact

- **Frontend** (`frontend/src/`): `widgets/layout/Navbar.tsx`, `widgets/layout/AppLayout.tsx`, `app/Router.tsx`, `pages/login/LoginPage.tsx` (vía LoginForm), nuevo `shared/ui/ToastContainer.tsx`.
- **authService**: Se consume `logout` para invalidar el token en el backend al cerrar sesión.
- **Sin cambios en backend**.
- **Rutas nuevas como placeholders**: `/cart`, `/profile`, `/addresses`, `/admin/categories`, `/admin/ingredients`, `/admin/orders`, `/admin/users`, `/admin/metrics` — todas con guards correctos, contenido temporal.
