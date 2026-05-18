# zustand-stores Specification

## Purpose
Define the Zustand store architecture and API for the food-store frontend, providing typed, atomic-selector-based state management for authentication (JWT + usuario profile), shopping cart (items, totals, personalization), payment checkout (transient flow state), and UI application state (theme, sidebar, toasts). Stores use localStorage persistence where appropriate (auth, cart, UI theme) and enforce separation of concerns (logout does not clear cart per RN-CR02). Implements US-000e acceptance criteria.
## Requirements
### Requirement: Auth store with JWT management
The system SHALL provide a `useAuthStore` (Zustand) that manages authentication state for the client: access token, refresh token, `usuario` profile (a `Usuario` with `id, email, nombre, roles[]` of type `Rol[]`), and an `isAuthenticated` flag. The naming `Usuario`/`Rol` mirrors the backend domain entities (`backend/features/users/models.py::Usuario`, `backend/features/catalog/models.py::Rol`) per the canonical spec (Integrador.txt:256). The store SHALL expose actions `login(tokens, usuario)`, `logout()`, and `updateTokens(tokens)`, and SHALL expose atomic selectors (`selectIsAuthenticated`, `selectAccessToken`, `selectHasRol(rol)`) so consumers can subscribe per-slice instead of the full store.

#### Scenario: authStore tracks authentication state on init
- **WHEN** the application initializes
- **THEN** `useAuthStore` rehydrates from `localStorage` key `food-store-auth`, restoring `accessToken`, `refreshToken`, `usuario`, and `isAuthenticated`

#### Scenario: login action populates the store
- **WHEN** `useAuthStore.getState().login({ accessToken, refreshToken }, usuario)` is invoked with a successful auth response
- **THEN** the store stores both tokens, the full `usuario` object (including `roles[]` as `Rol[]`), and sets `isAuthenticated = true`

#### Scenario: updateTokens action rotates the token pair
- **WHEN** `useAuthStore.getState().updateTokens({ accessToken, refreshToken })` is invoked after a refresh
- **THEN** both tokens are replaced atomically and `usuario` and `isAuthenticated` remain untouched

#### Scenario: logout clears auth state but does NOT touch the cart
- **WHEN** `useAuthStore.getState().logout()` is invoked
- **THEN** `accessToken`, `refreshToken`, and `usuario` become `null`, `isAuthenticated` becomes `false`, the persisted `food-store-auth` entry is cleared, AND `useCartStore` state remains unchanged (per RN-CR02)

#### Scenario: selectHasRol returns role membership
- **WHEN** a component calls `useAuthStore(selectHasRol('ADMIN'))` and the `usuario` has a `Rol` with `codigo: 'ADMIN'`
- **THEN** the selector returns `true`; otherwise it returns `false` (and `false` if `usuario` is `null`)

#### Scenario: getState() works outside React for the Axios interceptor
- **WHEN** non-React code calls `useAuthStore.getState().accessToken`
- **THEN** the current access token is returned synchronously without subscribing to changes

### Requirement: Cart store with item management

The system SHALL provide a `useCartStore` (Zustand) that manages the shopping cart entirely client-side (per RN-CR01) with items shaped as `CartItem = { producto_id, nombre, precio, cantidad, imagen_url?, personalizacion }` per the canonical spec (Integrador.txt:256, RN-CR05). The type name `CartItem` stays in English by spec mandate (no `Carrito` table exists in the backend, RN-CR01). Field names follow the backend Producto DTO (snake_case: `producto_id`, `imagen_url`). The store SHALL expose actions `addItem(producto, cantidad, personalizacion)`, `removeItem(producto_id)`, `updateQuantity(producto_id, cantidad)`, `clearCart()`, and atomic selectors `selectTotalItems`, `selectTotalPrice`, `selectGetItem(producto_id)`. The store SHALL operate independently of `useAuthStore`: cart mutations succeed with or without an authenticated user, and login/logout transitions SHALL NOT alter cart contents.

#### Scenario: cartStore persists items across sessions

- **WHEN** a user adds a product to the cart
- **THEN** `useCartStore` saves the items array to `localStorage` key `food-store-cart` and the cart survives page refresh, browser close, `useAuthStore.logout()` (RN-CR02), and `useAuthStore.login()` (anonymous-to-authenticated transition)

#### Scenario: addItem on existing product increments quantity (RN-CR03)

- **WHEN** `addItem(producto, cantidad, personalizacion)` is invoked and an item with the same `producto_id` already exists in the cart
- **THEN** the existing item's `cantidad` is incremented by `cantidad`, no duplicate entry is created

#### Scenario: addItem with new product creates a new entry

- **WHEN** `addItem` is invoked with a `producto_id` not present in the cart
- **THEN** a new `CartItem` is appended with the supplied `cantidad` and `personalizacion`

#### Scenario: addItem works without authenticated user

- **GIVEN** `useAuthStore.user === null`
- **WHEN** `addItem(producto, cantidad, personalizacion)` is invoked
- **THEN** the item is added to the cart identically to the authenticated case
- **AND** the store does NOT call `useAuthStore` or any backend endpoint

#### Scenario: updateQuantity to zero or below removes the item

- **WHEN** `updateQuantity(producto_id, n)` is invoked with `n <= 0`
- **THEN** the item is removed from the cart entirely

#### Scenario: selectTotalPrice computes subtotal from item snapshots

- **WHEN** the cart contains items with `precio` and `cantidad`
- **THEN** `selectTotalPrice(state)` returns the sum of `precio * cantidad` across all items

#### Scenario: clearCart empties the cart

- **WHEN** `clearCart()` is invoked (typically from a successful checkout flow, never from logout)
- **THEN** `items` becomes `[]` and the persisted entry reflects the empty cart

#### Scenario: Personalization stores excluded ingredient IDs (RN-CR05)

- **WHEN** an item is added with `personalizacion = { ingredientes_excluidos: [3, 7] }`
- **THEN** the cart item carries that exact array and the array is preserved on persist + rehydrate

### Requirement: Payment store with checkout flow state
The system SHALL provide a `usePaymentStore` (Zustand) that models the in-flight checkout/payment process with state `{ checkoutStep, preferenceId, paymentStatus, error }`. The store SHALL expose actions `startCheckout(pedidoId)`, `setPreference(preferenceId)`, `updatePaymentStatus(status)`, and `resetPayment()`. The store SHALL NOT persist to localStorage because the checkout state is inherently transient.

#### Scenario: startCheckout begins a payment flow
- **WHEN** `startCheckout(pedidoId)` is invoked
- **THEN** the store records the `pedidoId`, sets `checkoutStep` to the initial step, `paymentStatus` to `'pending'`, and `error` to `null`

#### Scenario: setPreference stores the MercadoPago preference id
- **WHEN** the backend returns a MercadoPago preference id and `setPreference(preferenceId)` is invoked
- **THEN** the store records the `preferenceId` so the UI can redirect or render the MP brick

#### Scenario: updatePaymentStatus advances the flow
- **WHEN** `updatePaymentStatus(status)` is invoked with `status` in `{ 'pending', 'processing', 'approved', 'rejected', 'error' }`
- **THEN** the store updates `paymentStatus` accordingly and components subscribed via selectors re-render

#### Scenario: resetPayment returns the store to its initial state
- **WHEN** `resetPayment()` is invoked (e.g., after a successful checkout, after error recovery, or on user cancel)
- **THEN** all fields return to their initial values

#### Scenario: paymentStore does NOT persist
- **WHEN** the user refreshes the page mid-checkout
- **THEN** `usePaymentStore` re-initializes with the default state (no `localStorage` rehydration, no stale `processing` flag)

### Requirement: UI store with application state
The system SHALL provide a `useUIStore` (Zustand) that manages UI-only state with `{ theme, sidebarOpen, toasts }` where `theme` is `'light' | 'dark'`, `sidebarOpen` is a boolean, and `toasts` is an array of `Toast` objects (`{ id, message, level, durationMs? }`). The store SHALL expose actions `setTheme(theme)`, `toggleSidebar()`, `pushToast(toast)`, and `dismissToast(id)`.

#### Scenario: setTheme persists the theme preference
- **WHEN** `setTheme('dark')` is invoked
- **THEN** the store updates `theme` to `'dark'`, persists only the `theme` slice to `localStorage` key `food-store-ui`, and does NOT persist `sidebarOpen` or `toasts`

#### Scenario: toggleSidebar flips visibility (transient, not persisted)
- **WHEN** `toggleSidebar()` is invoked
- **THEN** `sidebarOpen` flips and the change is NOT persisted (a fresh page load starts with the default value)

#### Scenario: pushToast and dismissToast manage the toast queue
- **WHEN** `pushToast({ id, message, level })` is invoked
- **THEN** the toast is appended to `toasts`, and `dismissToast(id)` removes the toast with matching `id` from the array

#### Scenario: theme survives page reload
- **WHEN** the user reloads the page after `setTheme('dark')`
- **THEN** `useUIStore` rehydrates `theme = 'dark'` and `sidebarOpen` / `toasts` start at their defaults

### Requirement: Store persistence with localStorage
The system SHALL persist selected store slices to `localStorage` using Zustand's `persist` middleware, with a per-store storage key and a `partialize` function that explicitly enumerates the persisted fields.

#### Scenario: Stores survive page refresh
- **WHEN** the user refreshes the page
- **THEN** `useAuthStore` (key `food-store-auth`), `useCartStore` (key `food-store-cart`), and `useUIStore` (key `food-store-ui`, theme only) restore state from `localStorage`

#### Scenario: paymentStore is intentionally not persisted
- **WHEN** the user refreshes the page
- **THEN** `usePaymentStore` re-initializes with default state (no persist middleware, no localStorage entry created)

#### Scenario: partialize excludes transient fields
- **WHEN** `useAuthStore` writes to localStorage
- **THEN** only the fields enumerated in `partialize` (`accessToken`, `refreshToken`, `usuario`, `isAuthenticated`) are stored; any future transient fields (e.g., `isLoading`) MUST be excluded

#### Scenario: Atomic selectors prevent full-store re-renders
- **WHEN** a component subscribes via an atomic selector (e.g., `useCartStore(selectTotalItems)`)
- **THEN** the component re-renders only when the selected slice changes, not when any other field of the store changes

### Requirement: Anonymous-safe cart store

The system SHALL allow `useCartStore` to operate with no authenticated user present in `useAuthStore`. Cart mutations (`addItem`, `removeItem`, `updateQuantity`, `clearCart`, `updateItemPrice`) SHALL succeed and persist regardless of `useAuthStore.user` being `null`. The store SHALL NOT consult `useAuthStore` to gate any cart operation. When an anonymous user logs in, `useAuthStore.login()` SHALL NOT clear, reset, or merge the cart against the server — the cart SHALL survive the login transition unchanged.

#### Scenario: Anonymous visitor adds an item to the cart

- **GIVEN** `useAuthStore.user === null`
- **WHEN** any UI calls `useCartStore.getState().addItem({ producto_id, nombre, precio, ... }, 1)`
- **THEN** the item is appended to `items` and persisted to `localStorage` key `food-store-cart`
- **AND** no error or guard rejection occurs

#### Scenario: Anonymous cart survives login

- **GIVEN** an anonymous visitor has items in `useCartStore`
- **WHEN** they complete a successful login (`useAuthStore.login(tokens, user)`)
- **THEN** `useCartStore.items` remains identical to before the login
- **AND** no network request to merge cart with the server is made

#### Scenario: Anonymous cart survives navigation between public catalog routes

- **GIVEN** an anonymous visitor adds items in `/cliente/catalogo`
- **WHEN** they navigate to `/cliente/catalogo/:id` and back, or refresh the page
- **THEN** `useCartStore.items` remains identical (rehydrated from `localStorage`)

#### Scenario: clearCart still works without an authenticated user

- **GIVEN** `useAuthStore.user === null` and `useCartStore.items` has at least one entry
- **WHEN** `useCartStore.getState().clearCart()` is invoked
- **THEN** `items` becomes `[]` and the persisted entry reflects the empty cart

### Requirement: Auth store does not persist tokens
The auth store SHALL NOT store or persist `accessToken` or `refreshToken`.

#### Scenario: Auth persistence contains no tokens
- **WHEN** auth state is persisted
- **THEN** only non-sensitive user/session fields are written to localStorage

