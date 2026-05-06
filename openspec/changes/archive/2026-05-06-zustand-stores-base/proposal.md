# Propuesta: zustand-stores-base

## Why

El frontend ya tiene scaffolding básico pero los cuatro stores de Zustand existen como stubs incompletos: tipos no alineados con la spec (Usuario no tiene array de roles, falta refreshToken, falta personalización en CartItem, paymentStore usa `selectedMethod` en vez del flujo de checkout, uiStore falta `toasts`), no exponen selectores atómicos, no exportan hooks idiomáticos (`useAuthStore`/`useCartStore`/etc.) y no tienen tests. Con `auth-backend` archivado y `auth-frontend-interceptor` en la próxima fase del Sprint 1, **el interceptor de Axios y el flujo de login dependen de un authStore con contrato firme** (`getState().accessToken`, `updateTokens()`, `logout()` que no toque `cartStore` por **RN-CR02**). Si arrancamos `auth-frontend-interceptor` sobre los stubs actuales, el interceptor se va a tener que reescribir cuando descubramos que el contrato no cierra. Esto cierra US-000e antes de que el resto del frontend lo necesite.

## What Changes

- **Re-spec y re-implementación de los cuatro stores** alineados a US-000e + RN aplicables (RN-AU02/AU03 para tokens, RN-CR01/CR02/CR03/CR05 para carrito):
  - `useAuthStore`: state `{ accessToken, refreshToken, usuario: Usuario | null, isAuthenticated }` con `Usuario = { id, email, nombre, roles: Rol[] }` (naming alineado con backend, Integrador.txt:256); actions `login(tokens, usuario)`, `logout()`, `updateTokens(tokens)`; selectors `selectIsAuthenticated`, `selectHasRol(rol)`, `selectAccessToken`. Persiste con clave `food-store-auth` y `partialize` que excluye estados transitorios.
  - `useCartStore`: state `{ items: CartItem[] }` con `CartItem = { producto_id, nombre, precio, cantidad, imagen_url?, personalizacion: { ingredientes_excluidos: number[] } }` (shape flat según Integrador.txt:256, RN-CR05); el nombre `CartItem` queda en inglés por mandato de la spec canónica (no hay tabla `Carrito` en backend, RN-CR01); actions `addItem`, `removeItem`, `updateQuantity`, `clearCart`; selectors `selectTotalItems`, `selectTotalPrice`, `selectGetItem(producto_id)`. Persiste con clave `food-store-cart`. **NO se limpia en logout (RN-CR02).**
  - `usePaymentStore`: state `{ checkoutStep, preferenceId, paymentStatus, error }`; actions `startCheckout(pedidoId)`, `setPreference(preferenceId)`, `updatePaymentStatus(status)`, `resetPayment()`. **Sin persistencia** (estado transitorio, RN explícita en spec).
  - `useUIStore`: state `{ theme: 'light'|'dark', sidebarOpen, toasts: Toast[] }`; actions `setTheme`, `toggleSidebar`, `pushToast`, `dismissToast`. Persistencia selectiva: solo `theme`.
- **Selectores atómicos exportados** por cada store como funciones `selectX` reutilizables — patrón que evita `useStore()` completo y previene re-renders innecesarios.
- **Renombrado del export**: `authStore` → `useAuthStore` (idiomático Zustand v5; `getState()` sigue funcionando para uso fuera de React, p.ej. interceptor Axios).
- **Tipos compartidos**: `Usuario`, `Rol`, `RolCode` y `AuthTokens` se mueven a `entities/user/model/types.ts`; `CartItem` y `Personalizacion` quedan en `entities/order/model/types.ts` (no en `shared/`). Los stores en `shared/stores/` los importan desde entities, respetando FSD.
- **Tests Vitest** por store (`*.test.ts`): cubren acciones principales, persistencia (mock localStorage) y selectores.
- **Documentación in-code**: cada store con JSDoc en su action map y un README breve en `shared/stores/README.md` con el patrón de selectores atómicos y la regla de `getState()` fuera de React.

No es BREAKING para producción (no hay producción todavía); sí reescribe los stubs de `frontend/src/shared/stores/` que se commitearon con `setup-frontend-core`.

## Capabilities

### New Capabilities

Ninguna nueva. Re-uso la capability existente — ver siguiente sección.

### Modified Capabilities

- `zustand-stores`: existe como spec con `Purpose: TBD` (creada al archivar `setup-frontend-core`). Esta change cierra el TBD, alinea los requirements al contrato real de US-000e, agrega el contrato del `paymentStore` (que estaba mal modelado como `selectedMethod`), agrega selectores atómicos como requirement, y aclara la regla de no-limpieza del carrito en logout (RN-CR02). El delta vive en `specs/zustand-stores/spec.md`.

## Impact

- **Código tocado** (`frontend/src/`):
  - `shared/stores/authStore.ts`, `cartStore.ts`, `paymentStore.ts`, `uiStore.ts` → reescritos.
  - `shared/stores/index.ts` → exporta hooks `useAuthStore`/etc. y selectores nombrados.
  - `shared/stores/README.md` → nuevo, documenta el patrón.
  - `entities/user/model/types.ts` → nuevo (Usuario, Rol, RolCode, AuthTokens).
  - `entities/order/model/types.ts` → nuevo (CartItem, Personalizacion).
  - `shared/stores/__tests__/*.test.ts` → suites Vitest para los cuatro stores.
- **Specs**:
  - `openspec/specs/zustand-stores/spec.md` → recibe Purpose + requirements re-alineados al cerrar el archive.
- **Downstream** (changes que dependen):
  - `auth-frontend-interceptor`: lee `useAuthStore.getState().accessToken` en interceptor de request, llama `updateTokens()` post-refresh, `logout()` en 401 inrecuperable. Este change le entrega ese contrato cerrado.
  - Cualquier change que toque carrito (`products-frontend-public`, `cart-checkout-frontend`) consumirá `useCartStore` con su API definitiva.
- **Sin impacto** en backend, BD, n8n, agente ni Docker. Cambio puramente de frontend.
- **Riesgos**: bajo — los stubs actuales no tienen consumidores reales en el repo (sólo están exportados desde `shared/stores/index.ts`, ningún componente los importa todavía).
