## ADDED Requirements

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

## MODIFIED Requirements

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
