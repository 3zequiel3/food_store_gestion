# Design: Migrate Auth to HttpOnly Cookies

## Technical Approach

Keep the existing JWT access token, opaque refresh token, DB hashing, rotation, and replay detection. Change only token transport: backend auth endpoints set/clear HttpOnly cookies; frontend stops reading/storing tokens and sends cookies automatically. Business endpoints keep their existing path/body/response contracts.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Cookie transport | `access_token` + `refresh_token` as HttpOnly cookies | Bearer/localStorage; refresh cookie + access memory | User chose option 2. It removes raw tokens from JS and keeps current JWT/refresh model. |
| Dev cookie flags | `HttpOnly=true`, `SameSite=Lax`, `Secure=false` | `Strict`; `None`; `Secure=true` | `Lax` balances CSRF mitigation and usability. `Secure=false` is required for current HTTP dev. |
| Cookie paths | access: `/api/v1`; refresh: `/api/v1/auth` | both root `/`; refresh only `/refresh` | Access must reach protected API routes. Refresh should only reach auth endpoints including logout. |
| Response shape | Auth endpoints return user/session metadata, not raw tokens | Keep `TokenPairResponse` public | Prevents token leakage through JSON while preserving auto-login UX. |
| CSRF | No CSRF token in this change; rely on `SameSite=Lax` + same-origin `/api` dev proxy | Double-submit CSRF token now | Proposal scoped CSRF token as deferred unless design requires it. Current same-origin proxy and Lax are acceptable for dev; revisit before cross-site production. |

## Data Flow

Login/register:

```txt
LoginForm ──POST /auth/login──> auth router ──AuthService.login──> TokenPairResponse internal
                                     │
                                     ├─ set HttpOnly access_token cookie
                                     ├─ set HttpOnly refresh_token cookie
                                     └─ return { user, expires_in }
```

Protected request:

```txt
apiClient request ──cookies auto-sent──> get_current_user(request)
                                      ├─ read access_token cookie
                                      ├─ decode JWT
                                      └─ load active Usuario + roles
```

Expired access token:

```txt
request 401 ──> auth interceptor ──POST /auth/refresh with cookies──> rotate refresh
      │                                      │
      └──────── retry original request <─────┘ new cookies set
```

Logout:

```txt
POST /auth/logout ──refresh cookie──> revoke refresh token ──clear both cookies──> 204
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/features/auth/cookies.py` | Create | Constants and helpers: set auth cookies, clear auth cookies, cookie max-age/path flags. |
| `backend/features/auth/schemas.py` | Modify | Add public `AuthSessionResponse` (`user`, `expires_in`, maybe `token_type: "cookie"`); keep internal token DTO if needed. |
| `backend/features/auth/router.py` | Modify | Inject `Response`; set cookies on login/register/refresh; read refresh cookie on refresh/logout; clear cookies on logout; `/me` uses cookie auth. |
| `backend/features/auth/dependencies.py` | Modify | Replace `OAuth2PasswordBearer` extraction with `Request.cookies["access_token"]`; update optional user similarly. |
| `backend/config.py` | Modify | Add auth cookie settings with dev defaults: secure false, samesite lax, names/paths. |
| `frontend/src/api/client.ts` | Modify | Set `withCredentials: true`. |
| `frontend/src/api/interceptors/auth.ts` | Modify | Remove Authorization header injection. On 401, single-flight `POST /auth/refresh` without body, then retry. |
| `frontend/src/features/auth/services/auth.service.ts` | Modify | Login/register return session response; refresh takes no argument; logout sends no token body. |
| `frontend/src/features/auth/stores/authStore.ts` | Modify | Remove token fields and localStorage persistence. Store `user` plus session status only. |
| `frontend/src/features/auth/hooks/*` | Modify | Persist user/session state only; rehydrate using `/auth/me`. |
| `openspec/specs/*` | Modify | Delta specs for auth, auth-service, http-client, routing-guards, zustand-stores. |

## Interfaces / Contracts

```py
COOKIE_ACCESS = "access_token"
COOKIE_REFRESH = "refresh_token"
ACCESS_PATH = "/api/v1"
REFRESH_PATH = "/api/v1/auth"
COOKIE_HTTPONLY = True
COOKIE_SECURE = False  # dev
COOKIE_SAMESITE = "lax"
```

```ts
type AuthSessionResponse = {
  user: Usuario;
  expires_in: number;
  token_type: 'cookie';
};
```

`POST /auth/refresh` no longer accepts `{ refresh_token }`; it reads `refresh_token` cookie. `POST /auth/logout` should be best-effort: revoke if refresh cookie exists, always clear cookies.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Cookie helper flags, paths, max-age | Direct helper assertions. |
| Backend integration | login/register set cookies; `/me` works with cookies; refresh rotates; logout clears | FastAPI TestClient cookie jar. |
| Frontend unit | auth store has no tokens/persist; interceptor refresh retries without Bearer | Vitest mocked axios/store. |
| Regression | Business endpoints still work when authenticated | Existing integration helpers updated to use cookies. |

## Migration / Rollout

No DB migration required. Existing refresh token rows remain valid. Frontend users with old `localStorage` tokens should be logged out or have auth storage cleared on app startup to avoid stale state.

## Open Questions

None. Production auto-switch to `AUTH_COOKIE_SECURE=true` is deferred to a follow-up.
