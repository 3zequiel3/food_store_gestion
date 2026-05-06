## 1. Pre-flight y tipos de dominio

- [x] 1.1 Verificar con `rg "from.*shared/stores"` y `rg "authStore\\.|cartStore\\.|paymentStore\\.|uiStore\\."` desde `frontend/src/` que ningún componente importa los stubs actuales por su nombre antiguo (esperado: 0 matches fuera de `shared/stores/index.ts`). Si aparece alguno, listarlo aquí antes de seguir.
  - Encontrados: App.tsx (uiStore), Navbar.tsx (authStore + uiStore), shared/api/client.ts (authStore.getState().token). Serán actualizados en task 6.1.
- [x] 1.2 Crear `frontend/src/entities/user/model/types.ts` con `RolCode`, `Rol`, `Usuario`, `AuthTokens` (tipos de design.md §"TypeScript types"). Los nombres `Usuario` y `Rol` mantienen el naming del backend (Integrador.txt:256, `backend/features/users/models.py::Usuario`, `backend/features/catalog/models.py::Rol`).
- [x] 1.3 Crear `frontend/src/entities/user/model/index.ts` que re-exporta los tipos.
- [x] 1.4 Crear `frontend/src/entities/order/model/types.ts` con `Personalizacion` y `CartItem`.
- [x] 1.5 Crear `frontend/src/entities/order/model/index.ts` que re-exporta los tipos.
- [x] 1.6 Crear `frontend/src/shared/types/ui.ts` con `Theme` y `Toast`. Actualizar `frontend/src/shared/types/index.ts` para re-exportar.

## 2. authStore

- [x] 2.1 Reescribir `frontend/src/shared/stores/authStore.ts`: definir `AuthState` con `accessToken`, `refreshToken`, `usuario` (tipo `Usuario | null`), `isAuthenticated`; usar `create<AuthState>()(persist(...))` con clave `food-store-auth`; implementar `login(tokens, usuario)`, `logout()`, `updateTokens(tokens)`. Naming del campo `usuario` viene de Integrador.txt:256.
- [x] 2.2 Configurar `partialize` para persistir `accessToken`, `refreshToken`, `usuario`, `isAuthenticated` (y nada más).
- [x] 2.3 Exportar selectores atómicos: `selectIsAuthenticated`, `selectAccessToken`, `selectRefreshToken`, `selectUsuario`, `selectHasRol(rol: RolCode)` (closure que devuelve un selector).
- [x] 2.4 Verificar que `logout()` solo limpia auth state y NO toca `useCartStore` (RN-CR02). Comentario en código que justifica la decisión apuntando a la spec.
- [x] 2.5 Crear `frontend/src/shared/stores/__tests__/authStore.test.ts` con tests: `beforeEach` resetea state via `useAuthStore.setState(initial, true)`; mock de `localStorage`; tests para `login`, `logout`, `updateTokens`, `selectHasRol` (con/sin usuario, con/sin rol), persistencia (rehydrate manual), y que `logout` NO afecta a `useCartStore`.

## 3. cartStore

- [x] 3.1 Reescribir `frontend/src/shared/stores/cartStore.ts`: definir `CartState` con `items: CartItem[]`; importar `CartItem` desde `entities/order/model`; usar `create<CartState>()(persist(...))` con clave `food-store-cart`.
- [x] 3.2 Implementar `addItem(producto, cantidad, personalizacion)`: si existe item con mismo `producto_id` incrementa `cantidad` (RN-CR03), si no, append. El parámetro `producto` aporta `producto_id`, `nombre`, `precio`, `imagen_url` para construir el `CartItem` flat (Integrador.txt:256).
- [x] 3.3 Implementar `removeItem(producto_id)` y `updateQuantity(producto_id, cantidad)`. Si `cantidad <= 0`, remover el item.
- [x] 3.4 Implementar `clearCart()`.
- [x] 3.5 Exportar selectores atómicos: `selectItems`, `selectTotalItems` (suma de `cantidad`), `selectTotalPrice` (suma de `precio * cantidad` por item, ya que `CartItem` es flat), `selectGetItem(producto_id)` (closure).
- [x] 3.6 `partialize` persiste todo el estado (`items`); no excluye nada — el carrito debe sobrevivir refresh y logout (RN-CR02).
- [x] 3.7 Crear `__tests__/cartStore.test.ts`: tests para `addItem` (nuevo + repetido = +cantidad), `removeItem`, `updateQuantity` (incl. caso `<=0` que remueve), `clearCart`, selectores, persistencia con personalización (`ingredientes_excluidos: [3,7]` debe sobrevivir rehydrate).

## 4. paymentStore

- [x] 4.1 Reescribir `frontend/src/shared/stores/paymentStore.ts`: definir `PaymentState` con `pedidoId`, `checkoutStep` (`'idle'|'address'|'method'|'processing'|'result'`), `preferenceId`, `paymentStatus` (`'pending'|'processing'|'approved'|'rejected'|'error'`), `error`. Usar `create<PaymentState>()` SIN middleware `persist`.
- [x] 4.2 Implementar acciones: `startCheckout(pedidoId)`, `setPreference(preferenceId)`, `updatePaymentStatus(status)`, `resetPayment()`.
- [x] 4.3 Exportar selectores: `selectCheckoutStep`, `selectPaymentStatus`, `selectPreferenceId`, `selectPaymentError`.
- [x] 4.4 Crear `__tests__/paymentStore.test.ts`: tests para cada acción, `resetPayment()` deja el state como inicial, y assert que NO se escribe nada en `localStorage` (verificar que `localStorage.getItem('food-store-payment')` sea `null` después de `startCheckout`).

## 5. uiStore

- [x] 5.1 Reescribir `frontend/src/shared/stores/uiStore.ts`: definir `UIState` con `theme: Theme`, `sidebarOpen: boolean`, `toasts: Toast[]`. Importar `Theme` y `Toast` desde `shared/types/ui`.
- [x] 5.2 Usar `create<UIState>()(persist(...))` con clave `food-store-ui`. `partialize` persiste **solo** `theme`.
- [x] 5.3 Implementar acciones: `setTheme(theme)`, `toggleSidebar()`, `pushToast(toast)`, `dismissToast(id)`.
- [x] 5.4 Exportar selectores: `selectTheme`, `selectSidebarOpen`, `selectToasts`.
- [x] 5.5 Aplicar la clase `dark` al `<html>` cuando `theme === 'dark'` mediante `onRehydrateStorage` y dentro de `setTheme` (mantiene el comportamiento del stub actual sin perderlo).
- [x] 5.6 Crear `__tests__/uiStore.test.ts`: tests para `setTheme` (persiste solo `theme`, aplica `dark` class), `toggleSidebar` (no persiste — verificar localStorage no contiene `sidebarOpen`), `pushToast`/`dismissToast`.

## 6. Index, README y wiring

- [x] 6.1 Reescribir `frontend/src/shared/stores/index.ts`: exportar `useAuthStore` y todos sus selectores; lo mismo para `useCartStore`, `usePaymentStore`, `useUIStore`. Re-exportar tipos desde `entities/*` cuando sea conveniente para los consumers.
  - También actualicé los 3 consumidores con nombres viejos: App.tsx (uiStore → useUIStore + selectTheme), Navbar.tsx (authStore/uiStore → useAuthStore/useUIStore con selectores), shared/api/client.ts (authStore.getState().token → useAuthStore.getState().accessToken).
- [x] 6.2 Crear `frontend/src/shared/stores/README.md` con: (a) lista de stores y persistencia, (b) patrón de selectores atómicos con ejemplo, (c) sección "Uso fuera de React" con el snippet de `useAuthStore.getState().accessToken` para el interceptor de Axios, (d) regla `logout()` no toca `cartStore` con referencia a RN-CR02.
- [x] 6.3 Verificar que `frontend/src/entities/index.ts` exporta los nuevos tipos (`Usuario`, `Rol`, `RolCode`, `AuthTokens`, `CartItem`, `Personalizacion`).
  - Actualicé entities/user/index.ts y entities/order/index.ts para exportar desde los nuevos subdirectorios model/. entities/index.ts ya los incluía vía export *.

## 7. Verificación final

- [x] 7.1 Correr `pnpm --dir frontend tsc -b` desde la raíz del repo (typecheck, sin emitir build). Esperado: 0 errores.
- [x] 7.2 Correr `pnpm --dir frontend test --run` (vitest una sola pasada). Esperado: todas las suites en verde, mínimo 1 test por acción y por selector documentado en specs.
  - Resultado: 55/55 tests pasan (5 suites). Gotcha resuelto: en Zustand v5, `setState` con persist middleware escribe inmediatamente al storage; en tests de rehydration, primero resetear el estado y luego escribir en localStorage para evitar que persist sobreescriba los datos de prueba. Usar `onFinishHydration` en lugar de `await rehydrate()` para esperar el set.
- [x] 7.3 Correr `pnpm --dir frontend lint`. Esperado: 0 errores.
- [x] 7.4 Smoke manual: `pnpm --dir frontend dev`, abrir DevTools → Application → Local Storage. Desde la consola del browser:
  - `useAuthStore.getState().login({ accessToken: 'a', refreshToken: 'r' }, { id: 1, email: 'x@x', nombre: 'X', roles: [{ id: 4, codigo: 'CLIENT' }] })` → verificar `food-store-auth` en localStorage.
  - `useCartStore.getState().addItem({ producto_id: 1, nombre: 'pizza', precio: 100 }, 2, { ingredientes_excluidos: [] })` → verificar `food-store-cart`.
  - `useAuthStore.getState().logout()` → verificar que `food-store-auth` se limpia pero `food-store-cart` SIGUE presente con el item.
  - Refresh F5 → verificar que el carrito sobrevive.
  - `useUIStore.getState().setTheme('dark')` → verificar `food-store-ui` solo contiene `theme`, NO `sidebarOpen`.
  - `usePaymentStore.getState().startCheckout(1)` → verificar que NO se crea `food-store-payment` en localStorage.
- [x] 7.5 Marcar todos los criterios de aceptación de US-000e como cubiertos en el resumen final del change.
  - useAuthStore: login, logout, updateTokens, selectHasRol, getState() fuera de React — cubiertos (specs §Auth store).
  - useCartStore: addItem (RN-CR03), removeItem, updateQuantity (<=0 remove), clearCart, selectTotalItems, selectTotalPrice, selectGetItem, personalizacion RN-CR05, persist RN-CR02 — cubiertos.
  - usePaymentStore: startCheckout, setPreference, updatePaymentStatus, resetPayment, NO persist — cubiertos.
  - useUIStore: setTheme (persiste solo theme), toggleSidebar (transient), pushToast/dismissToast, dark class — cubiertos.
- [x] 7.6 Correr `openspec validate zustand-stores-base --strict` y verificar 0 errores.
  - Resultado: "Change 'zustand-stores-base' is valid"
