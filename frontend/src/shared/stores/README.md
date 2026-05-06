# Zustand Stores

Four Zustand v5 stores. Each one owns a single domain slice. They do NOT
import from each other — cross-store orchestration lives in features or pages.

## Stores and persistence

| Store | localStorage key | Persists |
|---|---|---|
| `useAuthStore` | `food-store-auth` | `accessToken`, `refreshToken`, `usuario`, `isAuthenticated` |
| `useCartStore` | `food-store-cart` | `items` (full array, including `personalizacion`) |
| `useUIStore` | `food-store-ui` | `theme` only (`sidebarOpen` and `toasts` are transient) |
| `usePaymentStore` | — | **NOT persisted** — checkout state is intentionally transient |

## Pattern: atomic selectors

Each store exports named selectors. Subscribe to only the slice you need:

```tsx
import { useAuthStore, selectIsAuthenticated, selectHasRol } from '@/shared/stores'

// Component re-renders only when isAuthenticated changes
const isAuth = useAuthStore(selectIsAuthenticated)

// Closure selector for role membership
const isAdmin = useAuthStore(selectHasRol('ADMIN'))
```

Never subscribe to the full store (`useAuthStore()`) — it re-renders on every
state change across all fields.

## Usage outside React (Axios interceptor, utility functions)

```ts
import { useAuthStore } from '@/shared/stores'

// Read current token synchronously — works outside React
const token = useAuthStore.getState().accessToken

// Rotate tokens after a silent refresh
useAuthStore.getState().updateTokens({ accessToken: '...', refreshToken: '...' })

// Logout on 401 (in Axios response interceptor)
useAuthStore.getState().logout()
```

## RN-CR02 — logout() does NOT clear the cart

`useAuthStore.logout()` only clears auth state. The cart (`useCartStore`) is
intentionally left untouched so that a user who gets logged out (e.g., expired
session) comes back to find their cart intact.

If a specific flow needs to clear the cart together with logout (e.g., admin
impersonation), call `useCartStore.getState().clearCart()` explicitly from the
orchestrating code — not from inside `logout()`.

## Adding a new store

1. Create `frontend/src/shared/stores/xyzStore.ts`.
2. Define the state interface and `create<XyzState>()`.
3. Export the store hook and atomic selectors from this file.
4. Add exports to `index.ts`.
5. Write `__tests__/xyzStore.test.ts`.
6. If it needs persistence, pick a unique `food-store-*` key and add
   `partialize` to enumerate only the fields that should survive reload.
