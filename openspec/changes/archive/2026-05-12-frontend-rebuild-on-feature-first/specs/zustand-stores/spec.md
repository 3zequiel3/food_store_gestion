## REMOVED Requirements

### Requirement: Auth store with JWT management

**Reason**: The previous contract used method names `login(tokens, usuario)`, `logout()`, `updateTokens(tokens)` and atomic selectors `selectIsAuthenticated`, `selectAccessToken`, `selectHasRol(rol)`. The new auth store consolidates around `setSession` / `clearSession` / `getAccessToken` / `hasRole` for symmetry with how the interceptor and guards consume it.

**Migration**: See `Requirement: Auth store with persisted session` in `openspec/specs/frontend-foundation/spec.md`. The localStorage key (`food-store-auth`) is preserved.

### Requirement: Cart store with item management

**Reason**: The cart store contract is preserved in behavior (RN-CR01..05) but expressed against the new file layout (`frontend/src/features/cart/stores/cartStore.ts`) and the simplified action set.

**Migration**: See `Requirement: Cart store with localStorage persistence` in `frontend-foundation`. Personalization shape (`ingredientes_excluidos: number[]`) is preserved and will be re-introduced explicitly when Sprint 9 implements the cart UI; this change only mandates the store contract.

### Requirement: Payment store with checkout flow state

**Reason**: Deferred (decision D2). The payment flow is mostly transient state that fits TanStack Query + local component state. A store is only justified if a real cross-component need emerges in Sprint 10.

**Migration**: When the need is concrete, propose a change that adds `Requirement: Payment store with checkout flow state` under `frontend-foundation` (or a new `checkout` capability). Until then, no implementation exists.

### Requirement: UI store with application state

**Reason**: Deferred (decision D2). Sidebar open/close lives in local component state (`useState` inside `AppLayout`). Theme is not yet a user-facing toggle. Toasts are not yet wired (and may use `sonner` or similar instead of a custom store).

**Migration**: When a concrete need emerges (e.g., sidebar collapse must persist across reloads, dark mode toggle is implemented, or a global toaster is wired), propose a change that adds `Requirement: UI store with ...` under `frontend-foundation`.

### Requirement: Store persistence with localStorage

**Reason**: The previous requirement enumerated four stores. The new contract enumerates only the two stores actually created (auth + cart) under their own requirements; a generic "persistence" requirement is redundant.

**Migration**: Persistence is part of `Requirement: Auth store with persisted session` and `Requirement: Cart store with localStorage persistence` in `frontend-foundation`. Atomic-selector best practice is documented in `docs/frontend-architecture.md` antipatterns section.
