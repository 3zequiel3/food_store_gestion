# Proposal: Migrate Auth to HttpOnly Cookies

## Intent

Move `access_token` and `refresh_token` out of `localStorage` into backend-managed HttpOnly cookies. Current auth works, but XSS can read persisted tokens. Keep JWT semantics while improving transport.

## Scope

### In Scope
- Set `access_token` and `refresh_token` as HttpOnly cookies on login/register/refresh.
- Use `Secure=false` in dev and `SameSite=Lax` for both cookies.
- Authenticate backend requests from cookies instead of frontend Bearer headers.
- Stop persisting tokens in frontend `localStorage`; keep only non-sensitive session/user state.
- Configure Axios cookie sending and refresh behavior.
- Update specs and tests for cookie-backed auth.

### Out of Scope
- Production `Secure=true` rollout beyond documenting config.
- Server-side sessions/BFF architecture.
- Rewriting products, orders, payments, addresses, or admin endpoint contracts.
- CSRF token double-submit unless design finds it necessary.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `auth`: token delivery changes to HttpOnly cookies.
- `auth-service`: frontend stops consuming/persisting raw tokens.
- `http-client`: Axios sends cookies instead of injecting Bearer headers.
- `routing-guards`: session uses cookie-backed auth state.
- `zustand-stores`: auth store must not persist tokens.

## Approach

Keep JWT creation, refresh-token hashing, rotation, and replay detection. Change transport: routers set/clear cookies; `get_current_user()` reads the access cookie; refresh reads the refresh cookie. Frontend uses credentials/cookies and rehydrates user via auth responses or `/auth/me`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/features/auth/*` | Modified | Cookie set/read/clear and response contract. |
| `frontend/src/api/*` | Modified | Credentials config and interceptor behavior. |
| `frontend/src/features/auth/*` | Modified | Login/refresh/logout/store/session flow. |
| `openspec/specs/*` | Modified | Auth, client, routing, store contracts. |
| `backend/tests`, `frontend/src/**/*.test.*` | Modified | Cookie-aware auth expectations. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dev cookie/CORS mismatch | Med | Use same-origin `/api` proxy, `SameSite=Lax`, `Secure=false`. |
| CSRF exposure | Med | `SameSite=Lax`; evaluate CSRF token in design. |
| Tests expecting JSON tokens | High | Update tests to assert cookies/session behavior. |

## Rollback Plan

Revert the change folder and code to the current Bearer/localStorage contract. Token DB schema remains unchanged, so no migration rollback is needed.

## Dependencies

- Existing JWT and refresh-token rotation remain unchanged.
- Vite `/api` proxy should keep browser calls same-origin in dev.

## Success Criteria

- [ ] Tokens are not persisted in `localStorage`.
- [ ] Login/register/refresh set HttpOnly cookies with `SameSite=Lax`, `Secure=false` in dev.
- [ ] Protected endpoints work without frontend Bearer injection.
- [ ] Logout clears cookies and revokes refresh token.
- [ ] Business endpoint contracts remain unchanged.
