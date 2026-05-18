## Context

Hoy el catálogo del cliente vive bajo un nest `PrivateRoute → AppLayout → RoleGuard(['CLIENT']) → ClienteLayout`. Eso obliga al visitante anónimo a registrarse antes incluso de poder ver productos. La intención del producto es lo contrario: el catálogo es la vidriera pública, el muro de auth aparece recién en checkout.

Estado actual concreto (verificado en repo):

- `frontend/src/router/AppRoute.tsx`: las rutas `/cliente/catalogo` y `/cliente/catalogo/:id` están anidadas dentro de `PrivateRoute → AppLayout → RoleGuard(['CLIENT']) → ClienteLayout` (`AppRoute.tsx:74-115`).
- `frontend/src/components/layout/AppLayout.tsx`: provee `TopNavbar + Sidebar + BottomNav + CartDrawer` y asume usuario autenticado en su layout grid (`md:pl-16` reservado para Sidebar).
- `frontend/src/components/layout/TopNavbar.tsx`: ya lee `useAuthStore` y maneja `user === null`, pero hoy nunca se renderiza sin auth porque el Layout está detrás de `PrivateRoute`.
- `frontend/src/features/products/components/LandingProductCard.tsx:63-69`: handler `handleVerMas` ramifica por `isAuthenticated` y redirige a `/login` si no hay sesión.
- `frontend/src/features/cart/stores/cartStore.ts`: ya es 100% client-side, persiste en `localStorage` con key `food-store-cart`, sobrevive a logout (RN-CR02 vigente).
- `frontend/src/router/guards/PrivateRoute.tsx`: ya redirige a `/login` con `state.from = location.pathname` — pero `LoginForm.tsx:19-21` ignora `location.state` y navega siempre a `/`.

La spec canónica `routing-guards/spec.md` ya cubre el contrato base de PrivateRoute, redirect post-login con state.from y guards por rol — este change ajusta QUÉ rutas son públicas, no el mecanismo.

## Goals / Non-Goals

**Goals:**

- Cualquier visitante (sin sesión) puede entrar a `/cliente/catalogo` y `/cliente/catalogo/:id` y verlos completos, sin redirect.
- El muro de auth se materializa SOLO al intentar `/cliente/checkout`.
- El `LandingProductCard` cumple su contrato natural: "Ver más" abre el detalle del producto, sin depender de auth.
- El header de catálogo se adapta a la sesión: variantes pública (Iniciar sesión / Registrarse) y privada (avatar + perfil), sin duplicar componentes.
- El carrito anónimo es first-class: el visitante puede acumular ítems sin loguearse y, al ir a checkout, primero ve el muro de auth con redirect de vuelta al checkout — preservando el carrito intacto.

**Non-Goals:**

- Rediseño visual del catálogo o del header (lo cubre `checkout-single-page-ux` o un change estético dedicado).
- SEO/meta tags públicos del catálogo. Renderizar bien es suficiente para este change.
- Filtros o búsqueda nuevos en el catálogo. Los existentes se mantienen.
- Merge del carrito anónimo con un eventual carrito server-side: el backend no tiene tabla `Carrito` (RN-CR01), no hay nada que mergear.
- Mover otras rutas (`/cliente/perfil`, `/cliente/direcciones`, `/cliente/pedidos`) a públicas — siguen privadas.
- Cambiar el header de la landing ni la landing en sí.

## Decisions

### D1 — Layout para el catálogo público: `AppLayout` reutilizado, no `PublicAppLayout` nuevo

**Decisión**: Las rutas públicas del catálogo se renderizan dentro del mismo `AppLayout` actual, que se vuelve auth-aware. NO se crea un `PublicAppLayout` separado.

**Por qué**:

- `AppLayout` ya orquesta `TopNavbar + Sidebar + BottomNav + CartDrawer + MobileMoreDrawer`. Estos componentes ya leen `useAuthStore` defensivamente (`TopNavbar.tsx:11-25`, `BottomNav` solo se muestra mobile y ya esconde admin nav cuando no aplica).
- Duplicar layout (PublicAppLayout) genera divergencia: dos navbars distintas, dos drawers distintos, riesgo alto de bugs cuando uno se actualiza y el otro no.
- `Sidebar` SÍ asume sesión (tiene items por rol). Solución: `Sidebar` retorna `null` (o `<aside hidden />`) cuando `user === null`. El layout grid se ajusta condicionalmente (sin `md:pl-16` cuando no hay sidebar).
- El "AppLayout grande" no es un costo real para el visitante anónimo — los componentes ausentes simplemente no renderizan.

**Alternativa descartada**: `PublicAppLayout` independiente.

- Pros: separa concerns auth/no-auth claros.
- Contras: duplicación de TopNavbar (variantes en dos archivos), CartDrawer dos veces, dos bottom navs, dos sets de tests. Cualquier cambio de diseño de chrome hay que aplicarlo en dos lados. Para este proyecto (un solo dominio cliente) no compensa.

**Implementación**: el `<Route element={<AppLayout />}>` se saca del nest de `PrivateRoute` y queda al nivel de raíz; PrivateRoute + RoleGuard se aplican solo a las rutas que requieren auth (admin/* y cliente/* salvo catalogo).

### D2 — `TopNavbar` dual-mode con una sola instancia, NO dos navbars

**Decisión**: Una sola `TopNavbar` decide variantes leyendo `useAuthStore.user`. No se crea `PublicNavbar`.

**Variantes** (estado final):

- `user === null` (anónimo): logo "Food Store" + botón "Iniciar sesión" + botón "Registrarse" + icono carrito con badge (ver D6). Sin avatar, sin link a perfil.
- `user !== null + rol CLIENT`: logo + carrito con badge + avatar/perfil. (Comportamiento actual cliente.)
- `user !== null + roles staff (ADMIN/STOCK/PEDIDOS)`: logo + avatar/perfil sin carrito (comportamiento actual staff).

**Por qué**:

- `TopNavbar.tsx:11-25` ya lee `useAuthStore` y maneja `user === null` parcialmente — falta agregar los CTA Login/Registrarse cuando no hay sesión.
- Una sola fuente de verdad para el chrome. Tests cubren tres variantes con un solo componente.
- React 19 + Zustand selectors atómicos hacen que el costo de subscripción sea mínimo y solo re-renderiza la navbar cuando cambia `user`.

**Alternativa descartada**: `PublicNavbar` + `AuthenticatedNavbar`.

- Pros: cada componente más simple internamente.
- Contras: lógica de "qué navbar mostrar" se duplica en cada layout o en un wrapper; tests de transición (login/logout in-session) cuestan más.

### D3 — `cartStore` anónimo: sin merge, sin cambios funcionales

**Decisión**: el `cartStore` actual queda igual. NO se introduce merge con backend al hacer login. Solo se formaliza en spec que el anonymous cart es first-class.

**Por qué**:

- RN-CR01 explícita: "no existe tabla `Carrito` en el backend, el carrito es 100% frontend". No hay endpoint contra el que mergear.
- Persistencia ya funciona: `cartStore.ts:106-111` persiste en `localStorage` clave `food-store-cart` con `partialize` que solo guarda `items`.
- RN-CR02: `useAuthStore.logout()` NO toca el carrito. Esa garantía se aplica simétricamente al login: agregar productos sin sesión → loguearse → el carrito intacto sigue ahí.
- Riesgo "perder el carrito al loguearse" = cero, porque `useAuthStore.login()` también deja `cartStore` intacto (el store no se inicializa de nuevo, sigue siendo el mismo singleton de Zustand).

**Alternativa descartada**: merge server-side al hacer login (POST `/carrito/merge`).

- Pros: si en el futuro hubiera dispositivos cruzados, el carrito viajaría con el usuario.
- Contras: requiere endpoint y tabla nuevos, viola RN-CR01, complica testing. Out of scope.

### D4 — Solo catálogo se vuelve público; el resto de `/cliente/*` sigue privado

**Decisión**: Únicamente `/cliente/catalogo` y `/cliente/catalogo/:id` se mueven fuera de `PrivateRoute + RoleGuard(['CLIENT'])`. El resto de `/cliente/*` (perfil, direcciones, pedidos, pedidos/:id/confirmacion, checkout) permanece bajo el guard actual.

**Razón**:

- "Perfil" y "Direcciones" requieren un user_id real. No tienen sentido anónimos.
- "Pedidos" expone historial personal. No puede ser público.
- "Checkout" es exactamente donde queremos materializar el muro de auth (intent original del cambio).
- "Confirmación de pedido" se llega solo post-checkout, ya hay sesión por definición.

**Estructura final de routing**:

```
/                          → LandingPage (público, sin AppLayout)
/login, /register          → PublicRoute (redirige a / si auth) - sin AppLayout
/cliente/catalogo          → AppLayout (auth-aware) → CatalogPage (público)
/cliente/catalogo/:id      → AppLayout (auth-aware) → ProductDetailPage (público)
[PrivateRoute] → AppLayout → ClienteLayout (RoleGuard CLIENT)
  /cliente/perfil
  /cliente/direcciones
  /cliente/pedidos
  /cliente/pedidos/:id/confirmacion
  /cliente/checkout
[PrivateRoute] → AppLayout (RoleGuard ADMIN/STOCK/PEDIDOS)
  /admin/* (sin cambios)
```

Nota: `ClienteLayout` (envuelve con `<div className="p-4 md:p-6">`) hoy solo da padding adicional. Para preservar look-and-feel de las páginas públicas del catálogo, se mantiene ese wrapper en las rutas públicas (puede ser inline `<div className="p-4 md:p-6">` directo en el route element o un mini-componente `PublicCatalogShell` reusable).

### D5 — Redirect post-login: `location.state.from` (ya existe), NO query param

**Decisión**: Se preserva el contrato actual de `PrivateRoute` (guardar `state.from = location.pathname`). La obra pendiente es en `LoginForm`: consumir `location.state.from` (con fallback a `/`) y navegar ahí post-login. NO se introduce `?redirectTo=` query.

**Por qué**:

- `PrivateRoute.tsx:14-19` ya hace `<Navigate to="/login" state={{ from: location.pathname }} />`. El contrato existe — falta consumirlo del otro lado.
- `state.from` viaja in-memory, no contamina la URL ni queda expuesto en analytics/logs.
- Query param requiere sanitización (no permitir `redirectTo=https://evil.com`); state.from siempre es una path interna (lo escribimos nosotros).
- Si el usuario refresca `/login`, pierde el `state` y cae al fallback `/` — comportamiento aceptable (el flujo natural es: del checkout no se refresca login).

**Implementación**:

- `LoginForm.tsx:19-21`: cambiar `onSuccess: () => navigate('/')` por:
  ```ts
  onSuccess: () => {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    navigate(from, { replace: true });
  }
  ```
- Test: visitar `/cliente/checkout` sin sesión → redirige a `/login` → login OK → vuelve a `/cliente/checkout`.

**Alternativa descartada**: query param `?redirectTo=...`.

- Pros: sobrevive a refresh, se puede compartir URL.
- Contras: requiere sanitizar destino, expone intent en URL, sobreingeniería para nuestro caso.

### D6 — Carrito visible siempre en el header (anónimo incluido), badge cuando count > 0

**Decisión**: El botón del carrito aparece en `TopNavbar` siempre que el usuario NO sea staff — incluyendo visitantes anónimos. La badge con `totalItems` solo se renderiza cuando `totalItems > 0`.

**Por qué**:

- Si el visitante anónimo agrega productos pero no ve el icono del carrito, no sabe qué pasó: pierde affordance crítica.
- `TopNavbar.tsx:43-60` ya tiene esta lógica (`{!isAdmin && (...)}`) — y como `isAdmin` se calcula de roles, cuando `user === null` queda `false`, el icono ya aparecería. Hay que verificar que `useCartStore` se lee bien sin sesión (sí, es un store independiente).
- Badge condicional `{totalItems > 0 && ...}` ya existente — funciona idéntico anónimo.

**Confirmación práctica**: para anónimo el botón debe abrir el `CartDrawer` exactamente como hoy. El drawer ya lee del `cartStore`, no de `authStore`.

## Risks / Trade-offs

- **[Riesgo] `Sidebar` con `user === null`**: si Sidebar internamente asume `user.roles`, rompe. → **Mitigación**: en apply, `Sidebar` debe hacer guard temprano `if (!user) return null` o equivalente. Tests del layout público sin sesión cubren esto.

- **[Riesgo] Tests legacy de `LandingProductCard`** asumen que sin auth se va a `/login`. → **Mitigación**: actualizar `LandingProductCard.test.tsx` en el mismo change. Test RED se escribe primero (TDD).

- **[Riesgo] Componentes que consumen `useAuthStore` dentro de páginas públicas** (ej. `CatalogPage` o `ProductDetailPage`) podrían asumir `user !== null`. → **Mitigación**: revisar en apply. `CatalogPage.tsx` ya verificado — no usa `useAuthStore`. `ProductDetailPage` se verifica al implementar.

- **[Riesgo] Botón "Agregar al carrito" en el detalle del producto** podría dirigir a flujo de auth innecesariamente. → **Mitigación**: explícitamente, agregar al carrito NO requiere auth (D3). El muro de auth está en `/cliente/checkout`. El botón debe funcionar idéntico anónimo y autenticado.

- **[Trade-off] `AppLayout` se renderiza para anónimos**: tiene `useEffect` para cerrar drawers en navegación, `useState` para cartOpen/moreOpen/sidebarLocked. Es un poco más de bundle/runtime que un layout minimal. → **Aceptado** por D1: la simplicidad de tener un solo layout pesa más que el costo runtime marginal.

- **[Trade-off] No hay merge de carrito al loguearse**: si el usuario tiene carrito en device A (anónimo), se loguea en device B, no encuentra el carrito. → **Aceptado** por RN-CR01 y D3. Si en el futuro se quiere multi-device, será un change separado.

- **[Trade-off] `state.from` se pierde al refrescar `/login`**: edge case raro (¿quién refresca el login intencionalmente en medio de un flow?). Fallback a `/` es comportamiento defendible. → **Aceptado** por D5.

## Migration Plan

1. **Tests RED primero** (Strict TDD activo):
   - Test: visitante anónimo entra a `/cliente/catalogo` → CatalogPage renderiza.
   - Test: visitante anónimo entra a `/cliente/catalogo/123` → ProductDetailPage renderiza.
   - Test: visitante anónimo entra a `/cliente/checkout` → redirige a `/login` con `state.from === '/cliente/checkout'`.
   - Test: login con `state.from` → navega a `from` post-success.
   - Test: `LandingProductCard` con `isAuthenticated === false` → "Ver más" navega a `/cliente/catalogo/:id`.
   - Test: `TopNavbar` anónimo → muestra CTA Login/Registrarse, no avatar.
   - Test: `TopNavbar` anónimo → ícono carrito visible, badge con count cuando items > 0.

2. **Implementación incremental** (un commit por sub-slice):
   - Refactor `AppRoute.tsx`: extraer rutas catálogo del nest privado, montarlas con `AppLayout` directo.
   - Ajustar `Sidebar` para retornar null cuando `user === null` (si no lo hacía ya).
   - Ajustar `TopNavbar` para incluir CTA Login/Registrarse cuando `user === null`.
   - Actualizar `LandingProductCard.handleVerMas` (eliminar rama `/login`).
   - Actualizar `LoginForm.onSuccess` para usar `location.state.from`.

3. **Verify** (post-apply): correr `pnpm test` y `pnpm lint`. Visual check: `/cliente/catalogo` sin sesión renderiza completo.

4. **Rollback**: revertir el commit que mueve las rutas restaura el comportamiento previo. El `cartStore` no cambia código, no hay nada que revertir ahí.

## Open Questions

(Ninguna abierta para apply. Todas las decisiones críticas están cerradas arriba.)
