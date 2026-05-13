## ADDED Requirements

### Requirement: Feature-First plano module structure

The system SHALL organize frontend code under `frontend/src/` using **Feature-First plano** (NOT FSD nominal), with the following top-level directories: `api/`, `assets/`, `components/{common,layout,ui}/`, `features/<f>/{components,hooks,schemas,services,stores,types}/`, `lib/{constants,helpers,utils}/`, `pages/{admin,client,errors}/`, `router/`, plus `App.tsx`, `main.tsx`, and `index.css`. Each feature folder mirrors a backend feature by name where a counterpart exists (`features/auth` ↔ `backend/features/auth`). Frontend-only features (`cart`, `checkout`) are documented in `docs/frontend-architecture.md`.

#### Scenario: Feature-First plano directory exists

- **WHEN** the frontend is initialized
- **THEN** `frontend/src/` contains `api/`, `components/`, `features/`, `lib/`, `pages/`, `router/`, `assets/`, `App.tsx`, `main.tsx`, `index.css` and does NOT contain `entities/`, `widgets/`, or a top-level `shared/`

#### Scenario: Feature folders mirror backend features

- **WHEN** a developer creates a new feature with a backend counterpart (e.g., `addresses`)
- **THEN** the folder is named `features/addresses/` to match `backend/features/addresses/` exactly

#### Scenario: Each feature has the standard internal structure

- **WHEN** a feature is scaffolded
- **THEN** it contains `components/`, `hooks/`, `schemas/`, `services/`, `stores/`, and `types/` subfolders, all explicitly created (even if empty)

#### Scenario: Frontend-only feature is documented

- **WHEN** a feature without a backend counterpart is added (e.g., `cart`)
- **THEN** `docs/frontend-architecture.md` section 4 records the mapping as `(frontend-only)`

### Requirement: Axios client with relative baseURL and interceptor chain

The system SHALL provide a single `apiClient` instance in `frontend/src/api/client.ts` configured with `baseURL: '/api/v1'` (relative — resolved by Vite proxy in dev, by reverse proxy in prod), `timeout: 30_000`, default headers `Content-Type: application/json` and `Accept: application/json`. The client SHALL register the auth interceptor and error interceptor eagerly at module load time, before exporting `apiClient`.

#### Scenario: apiClient uses relative baseURL

- **WHEN** any feature service makes a request via `apiClient`
- **THEN** the URL is prefixed with `/api/v1` and resolved by the environment's HTTP layer (Vite proxy in dev, reverse proxy in prod), without any hardcoded host

#### Scenario: Default headers are set on every request

- **WHEN** any request is dispatched
- **THEN** the headers include `Content-Type: application/json` and `Accept: application/json`

#### Scenario: Request timeout is enforced

- **WHEN** a request exceeds 30 seconds without response
- **THEN** axios aborts the request and the error interceptor sees a timeout error

#### Scenario: Interceptors are wired at module load

- **WHEN** `apiClient` is imported anywhere in the app
- **THEN** the auth interceptor and the error interceptor are already attached — no additional wiring is required in `main.tsx` or feature code

### Requirement: Auth request interceptor with bearer injection

The system SHALL provide a request interceptor in `frontend/src/api/interceptors/auth.ts` that reads the access token from `useAuthStore.getState().getAccessToken()` synchronously and, if present, injects `Authorization: Bearer <token>` into the request headers. If no token is present, the request proceeds without an Authorization header.

#### Scenario: Authorization header is injected when token exists

- **WHEN** a request is dispatched and `useAuthStore.getState().getAccessToken()` returns a non-null string
- **THEN** the outgoing request includes `Authorization: Bearer <token>`

#### Scenario: Request proceeds without auth when no token

- **WHEN** a request is dispatched and `getAccessToken()` returns `null`
- **THEN** the outgoing request does NOT include an Authorization header

#### Scenario: Public endpoints work pre-login

- **WHEN** an unauthenticated user requests `/auth/login`
- **THEN** the request succeeds without an Authorization header

### Requirement: Response interceptor with single-flight refresh rotation

The system SHALL provide a response interceptor in `frontend/src/api/interceptors/auth.ts` that, on HTTP 401, attempts a single-flight refresh via `POST /auth/refresh` using the refresh token from `useAuthStore`. A module-level variable `refreshPromise: Promise<string> | null` SHALL hold the in-flight refresh. While `refreshPromise` is non-null, all concurrent 401 retries SHALL `await` the same promise instead of triggering additional refresh calls. On successful refresh, the new tokens are stored via `useAuthStore.getState().setSession(...)`, `refreshPromise` is set back to `null`, and all queued original requests retry with the new token. On failed refresh, `refreshPromise` is reset, `useAuthStore.getState().clearSession()` is called, and the user is redirected to `/login`.

#### Scenario: 401 triggers a refresh attempt when no refresh is in flight

- **WHEN** a response returns 401 and `refreshPromise` is `null`
- **THEN** the interceptor sets `refreshPromise` to a new `POST /auth/refresh` call and `await`s it

#### Scenario: Concurrent 401s share a single refresh

- **WHEN** three requests return 401 simultaneously and `refreshPromise` is already set
- **THEN** only one `POST /auth/refresh` is dispatched; the other two requests `await` the same promise and retry with the resulting new token

#### Scenario: Successful refresh retries the original request

- **WHEN** `POST /auth/refresh` succeeds and returns `{ access_token, refresh_token }`
- **THEN** `useAuthStore.getState().setSession(...)` is called with the new tokens, `refreshPromise` is reset to `null`, and the original 401-triggering request is retried with the new access token

#### Scenario: Failed refresh clears the session and redirects

- **WHEN** `POST /auth/refresh` rejects with any error
- **THEN** `useAuthStore.getState().clearSession()` is called, `refreshPromise` is reset to `null`, all queued retries reject, and `window.location.assign('/login')` is invoked

#### Scenario: 401 on the refresh endpoint itself does not loop

- **WHEN** `POST /auth/refresh` itself returns 401
- **THEN** the refresh is treated as failed (clearSession + redirect), and the interceptor does NOT attempt a further refresh

### Requirement: RFC 7807 error parser with ApiError class

The system SHALL provide an error interceptor in `frontend/src/api/interceptors/error.ts` that parses error responses and rejects the axios promise with an `ApiError` instance. `ApiError` SHALL be a class extending `Error` with read-only fields `{ type, title, status, detail, instance?, errors? }` where `errors` is an optional array of `{ field, message }` pairs. Non-RFC 7807 errors (network failures, timeouts, non-JSON bodies) SHALL also be wrapped in an `ApiError` with a generic shape (`type: 'about:blank'`, `title: 'Error de conexión'`, `status: 0`, `detail: 'No se pudo conectar al servidor'`).

#### Scenario: RFC 7807 response is parsed into ApiError

- **WHEN** the backend returns 400 with body `{ type, title, status, detail, instance }`
- **THEN** the interceptor rejects with `new ApiError(type, title, status, detail, instance)` and the consumer can read `e instanceof ApiError === true`

#### Scenario: Validation errors expose field-level details

- **WHEN** the backend returns 422 with body `{ type, title, status, detail, errors: [{ field: 'email', message: 'Email inválido' }] }`
- **THEN** the resulting `ApiError` has `errors` as an array containing `{ field: 'email', message: 'Email inválido' }`

#### Scenario: Network error becomes a generic ApiError

- **WHEN** axios fails with no response (network down, CORS, abort)
- **THEN** the interceptor rejects with an `ApiError` having `status: 0`, `title: 'Error de conexión'`, `detail: 'No se pudo conectar al servidor'`

#### Scenario: 401 errors are not silently swallowed

- **WHEN** the backend returns 401 and the auth interceptor's refresh logic fails
- **THEN** the final rejection still produces an `ApiError` so consumers can catch it (but the redirect has already occurred)

### Requirement: Auth store with persisted session

The system SHALL provide a `useAuthStore` (Zustand with `persist` middleware, storage key `food-store-auth`) that holds `{ accessToken, refreshToken, user }` where `user` includes `{ id, email, nombre, roles }` matching the backend `Usuario` shape. The store SHALL expose actions `setSession({ accessToken, refreshToken, user })`, `clearSession()`, and getters `getAccessToken()`, `getRefreshToken()`, `isAuthenticated()`, `hasRole(roleCode: string)`. The store SHALL be accessible from non-React code via `useAuthStore.getState()`.

#### Scenario: setSession persists tokens and user

- **WHEN** `useAuthStore.getState().setSession({ accessToken, refreshToken, user })` is invoked
- **THEN** the in-memory state and the `localStorage` entry `food-store-auth` both reflect the new session

#### Scenario: clearSession wipes session but not cart

- **WHEN** `useAuthStore.getState().clearSession()` is invoked
- **THEN** `accessToken`, `refreshToken`, and `user` become `null`, the persisted entry is cleared, AND `useCartStore` state remains untouched

#### Scenario: hasRole returns role membership

- **WHEN** a component calls `useAuthStore((s) => s.hasRole('ADMIN'))` and `user.roles` contains a role with `codigo: 'ADMIN'`
- **THEN** the selector returns `true`; if `user` is `null` or the role is absent, it returns `false`

#### Scenario: getState() works synchronously outside React

- **WHEN** the axios interceptor calls `useAuthStore.getState().getAccessToken()`
- **THEN** the current access token is returned synchronously without subscribing to changes

#### Scenario: Session survives page refresh

- **WHEN** the user refreshes the page after `setSession`
- **THEN** the store rehydrates from `food-store-auth` and `isAuthenticated()` returns `true`

### Requirement: Cart store with localStorage persistence

The system SHALL provide a `useCartStore` (Zustand with `persist` middleware, storage key `food-store-cart`) that manages the shopping cart 100% client-side. Items SHALL be shaped as `{ producto_id, nombre, precio, cantidad, imagen_url?, personalizacion? }` with snake_case fields mirroring the backend Producto DTO. The store SHALL expose actions `addItem`, `removeItem`, `updateQuantity`, `clearCart` and selectors for total items and total price. The cart SHALL survive `useAuthStore.clearSession()`.

#### Scenario: Cart persists across sessions

- **WHEN** the user adds items and refreshes the page
- **THEN** the items rehydrate from `localStorage` key `food-store-cart`

#### Scenario: Cart survives logout

- **WHEN** `useAuthStore.getState().clearSession()` is invoked while the cart has items
- **THEN** `useCartStore` retains all items

#### Scenario: addItem increments existing item quantity

- **WHEN** `addItem(producto, cantidad)` is called and an item with the same `producto_id` exists
- **THEN** the existing item's `cantidad` is incremented by `cantidad`; no duplicate row is appended

#### Scenario: updateQuantity to zero removes the item

- **WHEN** `updateQuantity(producto_id, 0)` is called
- **THEN** the item is removed from the cart

#### Scenario: Total price selector computes from snapshots

- **WHEN** the cart has items with `precio` and `cantidad`
- **THEN** the total price selector returns the sum of `precio * cantidad` across all items

### Requirement: Deferred Zustand stores not created upfront

The system SHALL NOT create `paymentStore` or `uiStore` in this change. Any future client state for the checkout flow, theme, sidebar persistence, or toasts SHALL be introduced only when a concrete component requires it.

#### Scenario: No payment store exists yet

- **WHEN** the repository is inspected after this change
- **THEN** `frontend/src/features/payments/stores/` does NOT contain a `paymentStore.ts` file

#### Scenario: No ui store exists yet

- **WHEN** the repository is inspected after this change
- **THEN** `frontend/src/components/` and `frontend/src/lib/` do NOT contain a global `uiStore.ts`

### Requirement: Auth schemas with Zod

The system SHALL provide Zod schemas in `frontend/src/features/auth/schemas/` for `loginSchema` (`{ email: z.email(), password: z.string().min(1) }`), `registerSchema` (`{ nombre, apellido (each min 2 max 80), email: z.email(), password: z.string().min(8) }`), and `passwordChangeSchema` (`{ current_password: z.string().min(1), new_password: z.string().min(8) }`). All error messages SHALL be in Spanish.

#### Scenario: loginSchema rejects invalid email

- **WHEN** `loginSchema.safeParse({ email: 'not-an-email', password: 'x' })` is called
- **THEN** the result is `{ success: false }` with a Spanish error message on `email`

#### Scenario: registerSchema enforces minimum password length

- **WHEN** `registerSchema.safeParse({ ..., password: '1234567' })` is called
- **THEN** the result fails with a Spanish error indicating "mínimo 8 caracteres"

#### Scenario: registerSchema requires apellido

- **WHEN** `registerSchema.safeParse({ nombre: 'Juan', apellido: '', email: 'a@b.c', password: '12345678' })` is called
- **THEN** the result fails with an error on `apellido`

#### Scenario: passwordChangeSchema requires both fields

- **WHEN** `passwordChangeSchema.safeParse({ current_password: '', new_password: '12345678' })` is called
- **THEN** the result fails on `current_password`

### Requirement: Auth service with typed endpoints

The system SHALL provide `frontend/src/features/auth/services/auth.service.ts` exposing async functions `login(credentials)`, `register(payload)`, `refresh(refreshToken)`, `logout()`, and `me()`. All functions SHALL import paths from `lib/constants/endpoints.ts` (no hardcoded URLs) and use `apiClient`. Responses SHALL be typed.

#### Scenario: login posts to ENDPOINTS.auth.login

- **WHEN** `authService.login({ email, password })` is called
- **THEN** it issues `apiClient.post(ENDPOINTS.auth.login, { email, password })` and returns a typed `LoginResponse`

#### Scenario: refresh posts the refresh_token to ENDPOINTS.auth.refresh

- **WHEN** `authService.refresh(refreshToken)` is called
- **THEN** it issues `apiClient.post(ENDPOINTS.auth.refresh, { refresh_token: refreshToken })`

#### Scenario: me reads ENDPOINTS.auth.me

- **WHEN** `authService.me()` is called and the user is authenticated
- **THEN** it issues `apiClient.get(ENDPOINTS.auth.me)` and returns the typed `Usuario`

#### Scenario: No service hardcodes a path

- **WHEN** the developer inspects `auth.service.ts`
- **THEN** every URL passed to `apiClient` is read from `ENDPOINTS.auth.*`, never as a string literal

### Requirement: Auth hooks built on TanStack Query

The system SHALL provide hooks `useLogin`, `useRegister`, `useLogout`, and `useMe` in `frontend/src/features/auth/hooks/`. `useLogin` and `useRegister` SHALL wrap `useMutation` and on success call `useAuthStore.getState().setSession(...)`. `useLogout` SHALL call `authService.logout()`, then `clearSession()`, then `queryClient.clear()`. `useMe` SHALL wrap `useQuery` with `queryKey: ['auth', 'me']` and `enabled: isAuthenticated()`.

#### Scenario: useLogin populates the auth store on success

- **WHEN** `useLogin().mutate({ email, password })` succeeds
- **THEN** `useAuthStore.getState().setSession({ accessToken, refreshToken, user })` is invoked with the response data

#### Scenario: useLogout clears session and query cache

- **WHEN** `useLogout().mutate()` resolves
- **THEN** `useAuthStore.getState().clearSession()` is called AND `queryClient.clear()` is called

#### Scenario: useMe only queries when authenticated

- **WHEN** the user is not authenticated and a component mounts that uses `useMe()`
- **THEN** no request is dispatched (the query is disabled)

#### Scenario: useMe refetches when authentication state flips

- **WHEN** the user authenticates after being unauthenticated
- **THEN** `useMe()` becomes enabled and the request is dispatched

### Requirement: Login and Register forms with TanStack Form + Zod

The system SHALL provide `LoginForm` and `RegisterForm` components in `frontend/src/features/auth/components/` using **TanStack Form** with a Zod adapter for validation. `react-hook-form` MUST NOT be imported anywhere. Forms SHALL validate `onBlur` by default (`onChange` only on short fields with immediate feedback), and re-validate on `onSubmit`. On 409 conflict (duplicate email in register), the form SHALL display an inline error. On 401 in login, it SHALL display "Credenciales inválidas" inline.

#### Scenario: LoginForm uses TanStack Form

- **WHEN** the developer inspects `LoginForm.tsx`
- **THEN** the imports include `@tanstack/react-form` and NOT `react-hook-form` or `@hookform/resolvers`

#### Scenario: RegisterForm validates with Zod on blur

- **WHEN** a user types in the email field and then blurs it with an invalid value
- **THEN** an inline Spanish error appears under the field

#### Scenario: 401 login error renders inline

- **WHEN** `useLogin().mutate(...)` rejects with `ApiError` and `status === 401`
- **THEN** the form displays "Credenciales inválidas" inside the form (NOT as a toast)

#### Scenario: 409 register error renders inline on the email field

- **WHEN** `useRegister().mutate(...)` rejects with `ApiError` and `status === 409`
- **THEN** the form displays a Spanish "email ya registrado" message attached to the email field

#### Scenario: Submit button shows loading state

- **WHEN** the form mutation is pending
- **THEN** the submit button is disabled and shows a loading indicator

### Requirement: Route tree with nested guards

The system SHALL configure `frontend/src/router/AppRoute.tsx` as a nested route tree where guard components (`PublicRoute`, `PrivateRoute`, `RoleGuard`) wrap parent routes and child routes render inside `<Outlet />`. `PublicRoute` SHALL redirect authenticated users to `/`. `PrivateRoute` SHALL redirect unauthenticated users to `/login` and preserve the original URL via `location.state.from`. `RoleGuard` SHALL check `useAuthStore.hasRole(...)` against the `roles` prop and redirect to `/403` if denied.

#### Scenario: Unauthenticated user on /login sees the login page

- **WHEN** an unauthenticated user navigates to `/login`
- **THEN** `PublicRoute` allows render and `LoginPage` is shown

#### Scenario: Authenticated user on /login redirects to /

- **WHEN** an authenticated user navigates to `/login`
- **THEN** `PublicRoute` redirects to `/`

#### Scenario: Unauthenticated user on /admin redirects to /login with from state

- **WHEN** an unauthenticated user navigates to `/admin/usuarios`
- **THEN** `PrivateRoute` redirects to `/login` and `location.state.from === '/admin/usuarios'`

#### Scenario: CLIENTE user on /admin sees Forbidden

- **WHEN** a user with role `CLIENTE` (no `ADMIN`/`STOCK`/`PEDIDOS`) navigates to `/admin/usuarios`
- **THEN** `RoleGuard` redirects to `/403`

#### Scenario: Unknown path renders NotFound

- **WHEN** any user navigates to `/this-does-not-exist`
- **THEN** the `NotFound` page (404) is rendered

### Requirement: Sidebar-based responsive layout

The system SHALL provide an `AppLayout` component composing `Sidebar` (left) and `Header` (top of content area) with a main content `<Outlet />`. The `Sidebar` SHALL be **persistent on viewports ≥768px** (md) and **overlay on viewports <768px** with a hamburger toggle in `Header` and a backdrop. The sidebar SHALL auto-close on route change when in mobile mode. The sidebar SHALL render different navigation items based on `useAuthStore.hasRole(...)`: ADMIN/STOCK/PEDIDOS see `usuarios, métricas, productos, pedidos, categorías, ingredientes`; CLIENTE sees `catálogo, carrito, mis pedidos, perfil, direcciones`.

#### Scenario: Sidebar is persistent on desktop

- **WHEN** the viewport width is ≥768px
- **THEN** the sidebar is rendered fixed on the left side, the main content area is offset to the right, and no backdrop is shown

#### Scenario: Sidebar is hidden by default on mobile

- **WHEN** the viewport width is <768px and the page first loads
- **THEN** the sidebar is hidden, the hamburger button is visible in the header, and no backdrop is shown

#### Scenario: Hamburger toggles overlay on mobile

- **WHEN** the user taps the hamburger on a <768px viewport
- **THEN** the sidebar slides in as an overlay with a backdrop covering the content

#### Scenario: Mobile sidebar auto-closes on navigation

- **WHEN** the sidebar is open on mobile and the user clicks a navigation link
- **THEN** the navigation occurs AND the sidebar closes automatically

#### Scenario: Sidebar items are role-aware

- **WHEN** the authenticated user has only `CLIENTE` role
- **THEN** the sidebar shows `catálogo, carrito, mis pedidos, perfil, direcciones` and does NOT show admin items

#### Scenario: Active route is highlighted

- **WHEN** the current location matches a sidebar item's path
- **THEN** that item is rendered with a visually distinct "active" style

### Requirement: Error pages for 401, 403, 404

The system SHALL provide three error pages in `frontend/src/pages/errors/`: `NotFound.tsx` (404), `Forbidden.tsx` (403), and `Unauthorized.tsx` (401). Each SHALL display a Spanish message, an explanatory body, and a primary action button to navigate back home or to login. The pages SHALL be reachable directly via routes `/404` (implicit via `*` wildcard), `/403`, `/401`.

#### Scenario: NotFound renders on unknown route

- **WHEN** the user navigates to `/anything-that-does-not-match`
- **THEN** the `NotFound` page renders with a Spanish "Página no encontrada" message and a "Volver al inicio" button

#### Scenario: Forbidden is reachable at /403

- **WHEN** the user (or a redirect from `RoleGuard`) navigates to `/403`
- **THEN** the `Forbidden` page renders with a Spanish "Acceso denegado" message

#### Scenario: Unauthorized is reachable at /401

- **WHEN** the user navigates to `/401`
- **THEN** the `Unauthorized` page renders with a Spanish "Sesión expirada" message and a "Iniciar sesión" button linking to `/login`

### Requirement: Design tokens via CSS custom properties and Tailwind theme

The system SHALL define design tokens as CSS custom properties under `:root` in `frontend/src/index.css` for colors (`--color-primary`, `--color-foreground`, `--color-background`, `--color-muted`, `--color-border`, `--color-success`, `--color-warning`, `--color-error`), spacing scale (if extending default), and radii. `frontend/tailwind.config.ts` SHALL extend `theme.colors` (and other relevant theme entries) to read these custom properties via `rgb(var(--color-x) / <alpha-value>)`. Components MUST NOT hardcode hex values; they SHALL use Tailwind utilities (`bg-primary`, `text-foreground`, etc.).

#### Scenario: Tokens are defined in index.css

- **WHEN** the developer inspects `index.css`
- **THEN** the file contains a `:root { ... }` block with at least `--color-primary`, `--color-foreground`, `--color-background`, `--color-error`, `--color-success` defined as RGB triplets

#### Scenario: Tailwind reads tokens via CSS variables

- **WHEN** a component uses `className="bg-primary text-foreground"`
- **THEN** the compiled CSS produces rules that use `rgb(var(--color-primary) / <alpha-value>)`

#### Scenario: No hardcoded hex in components

- **WHEN** an automated grep (`rg '#[0-9a-fA-F]{3,8}'`) is run over `frontend/src/components/` and `frontend/src/features/`
- **THEN** no matches are returned (or matches are explicitly justified in code review)

#### Scenario: Dark mode placeholder exists

- **WHEN** the developer inspects `index.css`
- **THEN** a `.dark { ... }` block exists as a placeholder for future dark theme tokens (even if currently empty or mirroring `:root`)

### Requirement: TanStack Query global defaults

The system SHALL configure the global `QueryClient` instance in `frontend/src/main.tsx` with defaults `{ queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false } }`. The QueryClient SHALL be wrapped around `<App />` via `<QueryClientProvider>`.

#### Scenario: QueryClient is configured with project defaults

- **WHEN** the application starts
- **THEN** all `useQuery` calls inherit `retry: 1`, `staleTime: 30_000`, `refetchOnWindowFocus: false` unless explicitly overridden

#### Scenario: QueryClientProvider wraps the app

- **WHEN** the developer inspects `main.tsx`
- **THEN** `<App />` is wrapped in `<QueryClientProvider client={queryClient}>`

#### Scenario: Mutations do not retry by default

- **WHEN** a mutation rejects
- **THEN** TanStack Query does NOT retry the mutation (default for mutations is no retry; defaults are not overridden to retry)

### Requirement: Mobile-first responsive design

The system SHALL design all layouts, forms, navigation, and tables **mobile-first**: base CSS classes SHALL target the smallest viewport (375px reference) and scale up with `sm:`, `md:`, `lg:` modifiers. Interactive elements SHALL have minimum touch targets of 44×44 CSS pixels. Forms SHALL render as single-column on mobile; two-column layouts only on `md:` and up. Tables SHALL reflow to a card list on viewports <768px (this requirement applies when tables are introduced in later changes — the design pattern is defined here).

#### Scenario: Touch targets meet minimum size

- **WHEN** the developer inspects any button or interactive element in the auth forms or sidebar
- **THEN** its rendered size at the smallest viewport is at least 44×44 CSS pixels

#### Scenario: Forms are single-column on mobile

- **WHEN** `LoginForm` or `RegisterForm` is rendered at viewport width 375px
- **THEN** all fields stack vertically in a single column

#### Scenario: Layout uses mobile-first base + larger-breakpoint overrides

- **WHEN** the developer inspects layout components
- **THEN** the base classes target mobile and larger viewports are introduced via `md:` / `lg:` prefixes (not the reverse)

### Requirement: Lucide React iconography with named imports only

The system SHALL use `lucide-react` for all icons. Imports SHALL be **named** (`import { Home } from 'lucide-react'`). Namespace imports (`import * as Icons from 'lucide-react'`) SHALL be prohibited via an ESLint rule. Icons SHALL be sized consistently via Tailwind classes (e.g., `<Home className="h-5 w-5" />`).

#### Scenario: lucide-react is installed

- **WHEN** the developer inspects `package.json`
- **THEN** `lucide-react` is listed as a dependency

#### Scenario: Components use named imports

- **WHEN** the developer inspects any component using an icon
- **THEN** the import is `import { IconName } from 'lucide-react'`, never `import * as ...`

#### Scenario: ESLint blocks namespace imports

- **WHEN** a developer writes `import * as Icons from 'lucide-react'` and runs `pnpm lint`
- **THEN** ESLint reports an error and the build/lint fails

#### Scenario: Icon sizes are consistent

- **WHEN** the developer inspects icon usage across components
- **THEN** sizes are applied via Tailwind utilities (`h-4 w-4`, `h-5 w-5`, `h-6 w-6`) rather than inline `size={...}` props with arbitrary numbers

### Requirement: react-hook-form is removed from dependencies

The system SHALL remove `react-hook-form` and `@hookform/resolvers` from `frontend/package.json`. The lockfile SHALL be regenerated via `pnpm install` so the dependencies are no longer present in `pnpm-lock.yaml`.

#### Scenario: react-hook-form is absent from package.json

- **WHEN** the developer inspects `frontend/package.json`
- **THEN** neither `react-hook-form` nor `@hookform/resolvers` appears in `dependencies` or `devDependencies`

#### Scenario: Lockfile no longer references react-hook-form

- **WHEN** the developer inspects `frontend/pnpm-lock.yaml`
- **THEN** no entry for `react-hook-form` or `@hookform/resolvers` exists

#### Scenario: No component imports react-hook-form

- **WHEN** an automated grep over `frontend/src/` looks for `react-hook-form` imports
- **THEN** no matches are returned
