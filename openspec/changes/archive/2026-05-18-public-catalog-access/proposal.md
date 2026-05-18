## Why

El catálogo del cliente (`/cliente/catalogo`, `/cliente/catalogo/:id`) está hoy detrás de `PrivateRoute + RoleGuard(['CLIENT'])`. Eso obliga al visitante a registrarse para BROWSE — la fricción es exactamente al revés de lo que queremos: cualquier visitante debería poder ver productos sin login, y el muro de auth solo debería aparecer cuando intenta INICIAR EL PEDIDO (checkout). Esto bloquea la conversión orgánica del landing y obliga al `LandingProductCard` a redirigir a `/login` en lugar del detalle real del producto.

Visión del usuario (verbatim): "el tema de catalogo, cliente y demas es todo accesible aun si no esta logueado, el problema radica cuando quiere hacer un pedido ahi si le tiene que pedir autenticarse".

## What Changes

- Mover las rutas `/cliente/catalogo` y `/cliente/catalogo/:id` **fuera** del wrapper `PrivateRoute + RoleGuard(['CLIENT'])` para que sean accesibles sin sesión.
- Mantener `/cliente/perfil`, `/cliente/direcciones`, `/cliente/pedidos`, `/cliente/pedidos/:id/confirmacion` y `/cliente/checkout` privados (sin cambios de guard).
- **BREAKING** para `LandingProductCard`: el botón "Ver más" ahora navega SIEMPRE a `/cliente/catalogo/:id` (eliminar la rama que redirige a `/login` cuando no hay sesión).
- Hacer que `TopNavbar` opere en modo dual con la misma instancia (decide variantes leyendo `useAuthStore`): muestra Login/Registrarse cuando no hay sesión y el avatar + acceso al perfil cuando sí, sin duplicar componentes.
- El `cartStore` (Zustand persist) ya sobrevive logout (RN-CR02); este change formaliza que también funciona sin sesión nunca creada (anonymous cart) y no requiere merge contra el servidor (el carrito es 100% client-side por RN-CR01).
- Mover el muro de auth a `/cliente/checkout`: visitar checkout sin sesión redirige a `/login` con el destino preservado (la actual `PrivateRoute` ya guarda `state.from`, falta consumir ese state desde `LoginForm` para volver post-login).
- Spec deltas en `routing-guards` (rutas del catálogo pasan a públicas, checkout sigue privado con redirect post-login estabilizado), `public-landing-page` (`LandingProductCard` nav siempre va al detalle) y `zustand-stores` (cartStore documentado como anonymous-safe sin merge contra server).

## Capabilities

### New Capabilities
<!-- No introducimos capabilities nuevas; reusamos las existentes con deltas. -->

### Modified Capabilities
- `routing-guards`: las rutas `/cliente/catalogo` y `/cliente/catalogo/:id` dejan de estar bajo `PrivateRoute + RoleGuard(['CLIENT'])` y pasan a públicas; `/cliente/checkout` sigue privada pero se formaliza el contrato de `redirectTo` post-login.
- `public-landing-page`: el `LandingProductCard` debe navegar SIEMPRE a `/cliente/catalogo/:id` (eliminar la rama que mandaba a `/login` sin sesión).
- `zustand-stores`: el `cartStore` se especifica explícitamente como anonymous-safe — no requiere usuario logueado para `addItem`, no realiza merge contra el servidor al hacer login, y persiste en `localStorage` independientemente del estado de auth.

## Impact

- **Frontend (código)**:
  - `frontend/src/router/AppRoute.tsx` — reorganización del árbol de rutas (mover `catalogo` y `catalogo/:id` fuera del nest privado, dentro o fuera de `AppLayout` según D1).
  - `frontend/src/features/products/components/LandingProductCard.tsx` — eliminar rama `!isAuthenticated → /login`.
  - `frontend/src/components/layout/TopNavbar.tsx` — variantes según `useAuthStore` (botones Login/Registrarse vs avatar+cart).
  - `frontend/src/features/auth/components/LoginForm.tsx` — consumir `location.state.from` (o `redirectTo` query) y navegar al destino post-login.
  - `frontend/src/router/guards/PrivateRoute.tsx` — sin cambios funcionales (ya guarda `state.from`).
  - `frontend/src/features/cart/stores/cartStore.ts` — sin cambios de código; solo formalización en spec (anonymous-safe).
- **Tests**:
  - Actualizar `LandingProductCard.test.tsx` (nuevo: `Ver más` siempre va al detalle, no depende de auth).
  - Nuevos tests de integración de routing (visitante anónimo entra a `/cliente/catalogo`, no es redirigido).
  - Nuevo test de `LoginForm` que verifica el redirect post-login a `state.from`.
- **Backend**: cero impacto. Los endpoints `GET /api/v1/productos` y `GET /api/v1/productos/:id` ya son públicos (RN-CA10).
- **Specs**: deltas en `routing-guards`, `catalog`, `zustand-stores`. Sin nuevas capabilities.
- **Dependencias**: ninguna nueva. Reusa `react-router-dom`, `zustand`, `useAuthStore`.
- **Roadmap**: este change formaliza una mejora UX necesaria antes de seguir con `checkout-single-page-ux` u otros refinamientos del flujo de pedido; no rompe DAG porque las capabilities afectadas ya están vigentes.
