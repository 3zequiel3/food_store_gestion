## REMOVED Requirements

### Requirement: Axios instance with base configuration

**Reason**: The previous requirement assumed `VITE_API_URL` from environment configuration. The current architecture uses a **relative baseURL** (`/api/v1`), resolved by Vite proxy in dev and reverse proxy in prod (decision F2 in `docs/frontend-architecture.md`). Re-specifying the same surface with the new contract avoids drift.

**Migration**: See `Requirement: Axios client with relative baseURL and interceptor chain` in `openspec/specs/frontend-foundation/spec.md`.

### Requirement: Request interceptor hooks

**Reason**: The previous spec described request interceptors abstractly without committing to the bearer injection contract. The new spec is concrete and testable.

**Migration**: See `Requirement: Auth request interceptor with bearer injection` in `frontend-foundation`.

### Requirement: Response interceptor hooks

**Reason**: The previous spec referenced `src/shared/api/client.ts` (FSD path that no longer exists) and `useUIStore` (deferred — no longer mandated). The refresh single-flight contract is preserved but expressed against the new file layout and store names.

**Migration**: See `Requirement: Response interceptor with single-flight refresh rotation` in `frontend-foundation`. The implementation lives at `frontend/src/api/interceptors/auth.ts` and uses `useAuthStore.setSession` / `clearSession` (not the old `login`/`logout`/`updateTokens` triplet).

### Requirement: RFC 7807 error handler

**Reason**: The previous `handleApiError` was a fire-and-forget toast pusher coupled to `useUIStore`. Without `useUIStore` (deferred per decision D2), this contract no longer fits. The error layer now rejects axios promises with a typed `ApiError` class so consumers can catch and decide how to surface (inline error in forms, toast where applicable, etc.).

**Migration**: See `Requirement: RFC 7807 error parser with ApiError class` in `frontend-foundation`. Future toast/snackbar integration will live in a separate change when `uiStore` (or an alternative like `sonner`) is introduced.

### Requirement: API response typing

**Reason**: The previous requirement was generic (`ApiResponse<T>`, `ApiError` as a type). The new contract makes `ApiError` a concrete class and pushes per-feature response typing to each feature's `types/` folder.

**Migration**: `ApiError` typing is covered by `Requirement: RFC 7807 error parser with ApiError class` in `frontend-foundation`. Feature-specific response types live under `frontend/src/features/<f>/types/` and are introduced incrementally by each feature change.
