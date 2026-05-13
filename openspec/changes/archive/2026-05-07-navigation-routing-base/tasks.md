## 1. ToastContainer

- [x] 1.1 Crear `src/shared/ui/ToastContainer.tsx` que lea `useUIStore(s => s.toasts)` y renderice cada toast como un div posicionado `fixed bottom-4 right-4 z-50 flex flex-col gap-2`
- [x] 1.2 Implementar auto-dismiss: `useEffect` por cada toast que llama `dismissToast(id)` después de `toast.durationMs ?? 4000` ms
- [x] 1.3 Renderizar botón × en cada toast que llame `dismissToast(id)` al hacer click
- [x] 1.4 Aplicar estilos por nivel: `error` → rojo, `success` → verde, `warning` → amarillo, `info` → azul
- [x] 1.5 Exportar `ToastContainer` desde `src/shared/ui/index.ts`

## 2. AppLayout

- [x] 2.1 Importar y montar `<ToastContainer />` dentro de `AppLayout.tsx` (antes del `<footer>`, dentro del wrapper principal)

## 3. Navbar — menú por rol

- [x] 3.1 Definir en `Navbar.tsx` los nav items por rol usando `selectHasRol` de `useAuthStore`:
  - CLIENT: `/products` (Catálogo), `/cart` (Mi Carrito), `/orders` (Mis Pedidos), `/profile` (Mi Perfil), `/addresses` (Mis Direcciones)
  - STOCK: `/admin/products` (Productos), `/admin/categories` (Categorías), `/admin/ingredients` (Ingredientes)
  - PEDIDOS: `/admin/orders` (Panel de Pedidos)
  - ADMIN: todos los anteriores + `/admin/users` (Usuarios), `/admin/metrics` (Métricas)
  - Sin auth: solo `/products` (Catálogo)
- [x] 3.2 Reemplazar los links hardcodeados actuales de la Navbar con el array de nav items computado por rol
- [x] 3.3 En mobile (`md:hidden`), renderizar al menos los links en un menú colapsable simple o stacked (no hamburger complejo)

## 4. Navbar — logout async

- [x] 4.1 Importar `logout` de `authService` y `selectRefreshToken` del authStore en `Navbar.tsx`
- [x] 4.2 Reemplazar `useAuthStore.getState().logout()` directo por un handler async que llama `authService.logout(refreshToken)` y en `.finally()` llama `useAuthStore.getState().logout()`
- [x] 4.3 Agregar `useNavigate` para redirigir a `/` después del logout

## 5. LoginForm — post-login redirect

- [x] 5.1 En `LoginForm.tsx`, importar `useLocation` de react-router-dom
- [x] 5.2 Reemplazar `navigate('/')` en el submit exitoso por `navigate(location.state?.from ?? '/', { replace: true })`

## 6. Router — todas las rutas

- [x] 6.1 Agregar rutas privadas sin restricción de rol: `/cart`, `/profile` (con `PrivateRoute`, placeholder)
- [x] 6.2 Agregar rutas privadas CLIENT: `/orders`, `/addresses` (con `PrivateRoute` + `RoleRoute allowedRoles={['CLIENT']}`, placeholder)
- [x] 6.3 Agregar rutas admin STOCK/ADMIN: `/admin/categories`, `/admin/ingredients` (con `PrivateRoute` + `RoleRoute allowedRoles={['ADMIN', 'STOCK']}`, placeholder)
- [x] 6.4 Agregar ruta PEDIDOS/ADMIN: `/admin/orders` (con `PrivateRoute` + `RoleRoute allowedRoles={['ADMIN', 'PEDIDOS']}`, placeholder)
- [x] 6.5 Agregar ruta solo ADMIN: `/admin/users`, `/admin/metrics` (con `PrivateRoute` + `RoleRoute allowedRoles={['ADMIN']}`, placeholder)
- [x] 6.6 Verificar que `/admin/products` ya tiene `RoleRoute allowedRoles={['ADMIN', 'STOCK']}` — ajustar si solo tiene `['ADMIN']`

## 7. Verificación

- [x] 7.1 `pnpm tsc --noEmit` sin errores
- [ ] 7.2 Smoke test: usuario CLIENT ve su menú correcto en navbar
- [ ] 7.3 Smoke test: usuario no autenticado intenta `/orders` → redirige a `/login` → post-login vuelve a `/orders`
- [ ] 7.4 Smoke test: error de API genera toast visible en pantalla (ej. login con credenciales incorrectas)
- [ ] 7.5 Smoke test: logout llama al backend (verificar en Network tab que se hace POST a `/api/v1/auth/logout`)
