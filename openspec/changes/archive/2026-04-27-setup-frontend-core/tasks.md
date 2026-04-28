## 1. Project Initialization

- [x] 1.1 Initialize Vite + React + TypeScript project in `frontend/` using `pnpm create vite@latest . -- --template react-ts`
- [x] 1.2 Install core dependencies: `react-router-dom`, `axios`, `zustand`
- [x] 1.3 Install dev dependencies: `tailwindcss`, `@tailwindcss/vite`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`
- [x] 1.4 Create `.env` with `VITE_API_URL=http://localhost:8000`
- [x] 1.5 Create `frontend/src/vite-env.d.ts` with typed environment variables (`VITE_API_URL`)
- [x] 1.6 Update `vite.config.ts` with proxy for `/api` to backend, Tailwind plugin

## 2. FSD Directory Structure

- [x] 2.1 Create FSD layer directories: `src/shared/`, `src/entities/`, `src/features/`, `src/widgets/`, `src/pages/`, `src/app/`
- [x] 2.2 Create `src/shared/` subdirectories: `api/`, `ui/`, `hooks/`, `types/`, `lib/`, `config/`
- [x] 2.3 Create `src/entities/` subdirectories: `user/`, `product/`, `order/`, `payment/`
- [x] 2.4 Create `src/features/` subdirectories: `auth/`, `cart/`, `products/`, `orders/`
- [x] 2.5 Create `src/pages/` subdirectories: `home/`, `login/`, `register/`, `products/`, `checkout/`, `orders/`, `admin/`, `errors/`
- [x] 2.6 Add `index.ts` barrel exports in each FSD layer directory

## 3. Tailwind CSS Configuration

- [x] 3.1 Create `frontend/src/index.css` with Tailwind directives (`@import "tailwindcss"`)
- [x] 3.2 Define design tokens in `tailwind.config.ts`: custom colors (primary, secondary, accent, success, warning, error), font family (Inter), spacing scale
- [x] 3.3 Add global styles: body font, background color, text color defaults
- [x] 3.4 Add dark mode support with `darkMode: 'class'` strategy

## 4. Environment Configuration

- [x] 4.1 Create `src/shared/config/env.ts` that reads and exports typed environment variables
- [x] 4.2 Export `API_URL`, `IS_DEV`, `IS_PROD` from config module
- [x] 4.3 Create `.env.example` documenting all required environment variables

## 5. HTTP Client (Axios)

- [x] 5.1 Create `src/shared/api/client.ts` with Axios instance configured with `VITE_API_URL`, default headers, 30s timeout
- [x] 5.2 Add request interceptor that attaches `Authorization: Bearer <token>` from authStore if available
- [x] 5.3 Add response interceptor for 401 handling (attempt token refresh, retry request, or logout)
- [x] 5.4 Create `src/shared/types/api.ts` with `ApiResponse<T>` and `ApiError` type definitions
- [x] 5.5 Export HTTP client from `src/shared/api/index.ts` barrel

## 6. Zustand Stores

- [x] 6.1 Create `src/shared/stores/authStore.ts` with: user, token, isAuthenticated, login(), logout(), setToken() actions; persist to localStorage (exclude refreshToken)
- [x] 6.2 Create `src/shared/stores/cartStore.ts` with: items[], addItem(), removeItem(), updateQuantity(), clearCart(), computed subtotal/total; persist to localStorage
- [x] 6.3 Create `src/shared/stores/paymentStore.ts` with: selectedMethod, status, externalId, setMethod(), setStatus() actions
- [x] 6.4 Create `src/shared/stores/uiStore.ts` with: sidebarOpen, darkMode, isLoading, toggleSidebar(), toggleDarkMode(), setLoading() actions; persist darkMode to localStorage
- [x] 6.5 Export all stores from `src/shared/stores/index.ts` barrel

## 7. Routing Infrastructure

- [x] 7.1 Create `src/app/Router.tsx` with react-router-dom v6 route definitions (public and private routes)
- [x] 7.2 Create `src/shared/ui/PrivateRoute.tsx` guard component that checks authStore.isAuthenticated, redirects to `/login` if not
- [x] 7.3 Create `src/shared/ui/PublicRoute.tsx` guard component that redirects authenticated users away from `/login` and `/register`
- [x] 7.4 Create `src/shared/ui/RoleRoute.tsx` guard component that checks user role, shows 403 if unauthorized
- [x] 7.5 Create `src/pages/errors/NotFound.tsx` (404 page) with link back to home
- [x] 7.6 Create `src/pages/errors/Forbidden.tsx` (403 page) with explanation
- [x] 7.7 Create placeholder pages: `src/pages/home/HomePage.tsx`, `src/pages/login/LoginPage.tsx`, `src/pages/register/RegisterPage.tsx`

## 8. App Shell and Layout

- [x] 8.1 Create `src/app/App.tsx` as root component with Router, theme provider (dark mode class on html)
- [x] 8.2 Create `src/widgets/layout/AppLayout.tsx` with navbar and main content area
- [x] 8.3 Create `src/widgets/layout/Navbar.tsx` placeholder with logo, nav links, auth buttons
- [x] 8.4 Update `src/main.tsx` to render App component with BrowserRouter

## 9. Entity Types

- [x] 9.1 Create `src/entities/user/types.ts` with User, Role, AuthState interfaces
- [x] 9.2 Create `src/entities/product/types.ts` with Product, Category, Ingredient interfaces
- [x] 9.3 Create `src/entities/order/types.ts` with Order, OrderItem, EstadoPedido enum, OrderState interfaces
- [x] 9.4 Create `src/entities/payment/types.ts` with Payment, FormaPago enum, PaymentStatus interfaces
- [x] 9.5 Export all entity types from barrel files

## 10. Testing Setup

- [x] 10.1 Configure `vitest` in `vite.config.ts` with test environment (jsdom), setup files
- [x] 10.2 Create `src/test/setup.ts` with `@testing-library/jest-dom` imports
- [x] 10.3 Create `src/app/__tests__/App.test.tsx` with basic render test
- [x] 10.4 Run `pnpm test` and verify tests pass

## 11. Final Verification

- [x] 11.1 Run `pnpm dev` — app starts on `http://localhost:5173` without errors
- [x] 11.2 Verify health check: navigate to home page, see placeholder content
- [x] 11.3 Verify dark mode toggle works (class added to html element)
- [x] 11.4 Run `pnpm build` — production build completes without errors
