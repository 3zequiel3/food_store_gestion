## 1. Tests RED — routing público del catálogo

- [x] 1.1 En `frontend/src/router/__tests__/` (crear si no existe), escribir test que renderice `AppRoute` con `MemoryRouter` y `useAuthStore` en estado anónimo, navegue a `/cliente/catalogo`, y verifique que se renderiza `CatalogPage` sin redirect a `/login`. Debe fallar (RED).
- [x] 1.2 Mismo test pattern: navegar a `/cliente/catalogo/123` con anónimo, verificar que se renderiza `ProductDetailPage` sin redirect. Debe fallar (RED).
- [x] 1.3 Test: visitante anónimo navega a `/cliente/checkout`, verificar redirect a `/login` con `location.state.from === '/cliente/checkout'`. Debe pasar (ya existe el comportamiento) — si falla, escribir el aserto para que sea explícito.
- [x] 1.4 Test: visitante anónimo navega a `/cliente/perfil`, verificar redirect a `/login` con `state.from === '/cliente/perfil'` (regresión: el resto de `/cliente/*` sigue privado).
- [x] 1.5 Correr `pnpm test` y confirmar que 1.1 y 1.2 fallan, 1.3 y 1.4 pasan.

## 2. Tests RED — LoginForm post-login redirect

- [x] 2.1 En `frontend/src/features/auth/components/__tests__/LoginForm.test.tsx` (crear si no existe), escribir test: renderizar `LoginForm` dentro de `MemoryRouter` con `initialEntries: [{ pathname: '/login', state: { from: '/cliente/checkout' } }]`, hacer login OK, verificar que `navigate` se llamó con `/cliente/checkout` y `{ replace: true }`. Debe fallar (RED).
- [x] 2.2 Test fallback: misma estructura sin `state.from`, verificar que `navigate` se llama con `/`. Debe pasar hoy — escribir aserto.
- [x] 2.3 Correr `pnpm test`. Confirmar 2.1 falla.

## 3. Tests RED — LandingProductCard navegación uniforme

- [x] 3.1 En `frontend/src/features/products/components/__tests__/LandingProductCard.test.tsx`, ajustar/escribir test: anónimo clickea "Ver más" → `navigate` se llamó con `/cliente/catalogo/:id`. Hoy navega a `/login` — el test nuevo debe fallar (RED).
- [x] 3.2 Mantener test: autenticado clickea "Ver más" → `navigate` se llamó con `/cliente/catalogo/:id` (sin cambios).
- [x] 3.3 Correr `pnpm test`. Confirmar 3.1 falla.

## 4. Tests RED — TopNavbar dual-mode y carrito anónimo

- [x] 4.1 En `frontend/src/components/layout/__tests__/TopNavbar.test.tsx` (crear si no existe), escribir test: `useAuthStore.user === null` → la navbar muestra botones/links "Iniciar sesión" y "Registrarse" (visibles por texto accesible), NO muestra avatar/initials. Debe fallar (RED — hoy no existen los CTAs públicos).
- [x] 4.2 Test: `useAuthStore.user === null` y `useCartStore.items.length > 0` → el botón del carrito renderiza con badge mostrando `totalItems`. Debe pasar hoy (lógica `!isAdmin` lo permite) — escribir aserto para fijar el contrato.
- [x] 4.3 Test: `useAuthStore.user === null` y carrito vacío → botón del carrito visible sin badge. Pasa hoy — aserto.
- [x] 4.4 Test: `useAuthStore.user !== null` rol CLIENT → muestra avatar + carrito (sin CTAs públicos). Aserto.
- [x] 4.5 Test: `useAuthStore.user !== null` rol staff (ADMIN) → avatar visible, carrito NO visible. Pasa hoy — aserto.
- [x] 4.6 Correr `pnpm test`. Confirmar 4.1 falla.

## 5. Tests RED — Cart store anonymous-safe

- [x] 5.1 En `frontend/src/features/cart/stores/__tests__/cartStore.test.ts` (crear si no existe; si existe, agregar describe), escribir test: con `useAuthStore.user === null`, `addItem(...)` agrega correctamente al cart, persiste en localStorage. Debe pasar hoy — fijar contrato.
- [x] 5.2 Test: anonymous cart con items, llamar `useAuthStore.getState().login(tokens, user)`, verificar que `useCartStore.getState().items` queda idéntico (no se reinicia ni se merge contra servidor). Debe pasar — aserto.
- [x] 5.3 Test: verificar que `cartStore.ts` NO importa `useAuthStore` ni ejecuta calls al backend en ninguna action (snapshot-test del archivo o mock del fetch + aserto que no se llamó).
- [x] 5.4 Correr `pnpm test`. Confirmar 5.1-5.3 pasan (o fallan si hay un gap real — entonces se arregla en GREEN).

## 6. GREEN — Refactor de routing en `AppRoute.tsx`

- [x] 6.1 En `frontend/src/router/AppRoute.tsx`, extraer las dos rutas `/cliente/catalogo` y `/cliente/catalogo/:id` del nest `<PrivateRoute><AppLayout><RoleGuard CLIENT><ClienteLayout>` y montarlas a nivel raíz envueltas solo en `<AppLayout>` (auth-aware). Mantener el wrapper de padding `<div className="p-4 md:p-6">` inline o vía un mini-componente `PublicCatalogShell`.
- [x] 6.2 Verificar que el resto de las rutas `/cliente/*` (perfil, direcciones, pedidos, pedidos/:id/confirmacion, checkout) siguen dentro del nest `PrivateRoute → AppLayout → RoleGuard CLIENT → ClienteLayout`.
- [x] 6.3 Verificar que `/admin/*` no se toca.
- [x] 6.4 Correr `pnpm test` y confirmar que 1.1 y 1.2 ahora pasan.

## 7. GREEN — Sidebar y AppLayout auth-aware

- [x] 7.1 En `frontend/src/components/layout/Sidebar.tsx`, si Sidebar asume `user.roles`, agregar guard temprano: si `useAuthStore.user === null`, retornar `null`. Test snapshot/render para confirmar.
- [x] 7.2 En `frontend/src/components/layout/AppLayout.tsx`, verificar que el grid se acomoda cuando Sidebar retorna null (sin clase `md:pl-16`). Si hace falta, condicionar `md:pl-16` a `user !== null` (o leerlo via `sidebarLockedOpen` siguiendo el patrón existente).
- [x] 7.3 Sanity-check: visitar `/cliente/catalogo` en dev server (manual) anónimo y autenticado — el layout no se rompe en ninguno.

## 8. GREEN — TopNavbar variantes Login/Registrarse

- [x] 8.1 En `frontend/src/components/layout/TopNavbar.tsx`, agregar bloque cuando `user === null`: dos `<Link to="/login">` y `<Link to="/register">` con clases que combinen con el chrome glassmorphism existente. Texto: "Iniciar sesión" y "Registrarse".
- [x] 8.2 Asegurar que NO se muestran avatar/initials cuando `user === null` (ya no se hace por el `{user && (...)}` actual).
- [x] 8.3 Asegurar que el ícono del carrito se sigue mostrando para usuarios anónimos (la lógica `{!isAdmin && (...)}` ya lo permite porque `isAdmin === false` para anónimo).
- [x] 8.4 Correr `pnpm test`. Confirmar 4.1 pasa.

## 9. GREEN — LandingProductCard nav uniforme

- [x] 9.1 En `frontend/src/features/products/components/LandingProductCard.tsx`, eliminar la rama `if (isAuthenticated) ... else navigate('/login')` en `handleVerMas`. Dejar solo `navigate(\`/cliente/catalogo/${producto.id}\`)`.
- [x] 9.2 Eliminar el import `useAuthStore` si ya no se usa en el archivo.
- [x] 9.3 Correr `pnpm test`. Confirmar 3.1 pasa.

## 10. GREEN — LoginForm consume `state.from`

- [x] 10.1 En `frontend/src/features/auth/components/LoginForm.tsx`, agregar `import { useLocation } from 'react-router-dom'` y `const location = useLocation()` en el componente.
- [x] 10.2 Cambiar `onSuccess: () => navigate('/')` por:
  ```ts
  onSuccess: () => {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    navigate(from, { replace: true });
  }
  ```
- [x] 10.3 Correr `pnpm test`. Confirmar 2.1 y 2.2 pasan.

## 11. GREEN — Validar contrato cartStore anonymous-safe

- [x] 11.1 Confirmar visualmente que `frontend/src/features/cart/stores/cartStore.ts` NO importa `useAuthStore` ni hace fetch en ninguna action (cierra contrato 5.3 sin cambio de código).
- [x] 11.2 Si el repo tiene algún sitio que llame `useCartStore.clearCart()` desde `useAuthStore.login()` (cross-store side effect), eliminarlo. Buscar con `rg "clearCart|useCartStore" frontend/src/features/auth/`.
- [x] 11.3 Correr `pnpm test`. Confirmar 5.1-5.3 pasan.

## 12. Validación final y commits

- [x] 12.1 Correr `pnpm test --run` (toda la suite). Confirmar 100% verde.
- [x] 12.2 Correr `pnpm lint`. Confirmar 0 errores nuevos (2 pre-existing sin cambios).
- [x] 12.3 Correr `pnpm tsc --noEmit` (type-check). Confirmar 0 errores.
- [x] 12.4 Sanity manual: levantar `pnpm dev` (frontend) + backend. En incógnito:
  - Abrir `/cliente/catalogo` → ver productos.
  - Click "Ver más" → ver detalle.
  - Agregar al carrito → ver badge.
  - Ir a `/cliente/checkout` → redirige a `/login`.
  - Login → vuelve a `/cliente/checkout` con carrito intacto.
- [x] 12.5 Correr `openspec validate public-catalog-access` y confirmar "is valid".
- [x] 12.6 Commits estilo conventional, sin "Co-Authored-By":
  - `refactor(router): hacer públicas las rutas /cliente/catalogo y /cliente/catalogo/:id`
  - `feat(navbar): variantes login/registrarse para usuarios anónimos`
  - `refactor(products): LandingProductCard navega siempre al detalle`
  - `feat(auth): LoginForm respeta state.from para redirect post-login`
  - (Si hubo ajustes en Sidebar/AppLayout): `fix(layout): Sidebar oculto cuando no hay sesión`
