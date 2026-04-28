## Context

The Food Store frontend requires a modern React architecture that supports:
- **Feature-Sliced Design (FSD)**: Code organized by business features, not technical layers
- **Type Safety**: Full TypeScript coverage for type checking and developer experience
- **State Management**: Client-side state for auth, cart, payments without backend coupling
- **Routing**: Public (landing, login, products) and private (checkout, order history, admin) routes with role-based access
- **Styling**: Atomic design with Tailwind CSS, responsive mobile-first design
- **HTTP Communication**: Axios with automatic JWT handling (added in auth-frontend-interceptor change)
- **Development Experience**: Hot module reload (HMR), fast build times, type checking on save

Currently: No frontend exists. This change creates the scaffolding and base patterns that all downstream features will follow.

## Goals / Non-Goals

**Goals:**
- Establish React 18 project with Vite for fast builds and HMR
- Implement Feature-Sliced Design (FSD) directory structure with layers: shared → entities → features → widgets → pages → app
- Create routing infrastructure with public/private guards
- Set up Zustand stores with localStorage persistence
- Configure Tailwind CSS with design tokens
- Create HTTP client (Axios) with interceptor hooks
- Set up vitest for component testing

**Non-Goals:**
- Implementing specific features (auth, products, cart) — done in later changes
- Designing specific UI components — Design System change handles that
- Payment integration UI — done in payment-frontend change
- Admin dashboard layout — done in admin-pages change

## Decisions

### Decision 1: Feature-Sliced Design (FSD) Architecture
**Choice**: Organize code into FSD layers: shared (utilities, UI kits) → entities (domain objects) → features (business features) → widgets (composite components) → pages (route-level pages) → app (root)

**Rationale**:
- Scalable: Large teams can work in parallel on different features
- Feature-focused: Business logic co-located with UI
- Easier refactoring: Move/remove entire features without side effects
- Clear dependency graph: Lower layers can't import from higher layers

**Example structure**:
```
src/
├── shared/          # Reusable across features (UI kits, hooks, types)
├── entities/        # Domain objects (User, Product, Order types)
├── features/        # Business features (Auth, Products, Cart, Orders)
├── widgets/         # Composite UI components
├── pages/           # Route-level pages (Login, Products, Checkout)
└── app/             # Root component, theme provider, router
```

**Alternative considered**: Layered by type (components/, services/, hooks/). ❌ Poor for feature ownership; features scattered across directories.

### Decision 2: Zustand for State Management
**Choice**: Use Zustand (not Redux) for client state: authStore, cartStore, paymentStore, uiStore

**Rationale**:
- Minimal boilerplate (1/10th Redux code)
- Built-in immer for immutable updates
- Devtools support for debugging
- localStorage integration via persist middleware
- Perfect for non-complex client state (no middleware chains needed)

**Alternative considered**: Redux. ❌ Overkill for Food Store; Zustand is sufficient.
**Alternative considered**: Context API. ❌ Prop drilling; hard to optimize re-renders.

### Decision 3: Tailwind CSS Over CSS-in-JS
**Choice**: Use Tailwind CSS for styling with pre-defined design tokens (colors, spacing, typography)

**Rationale**:
- Faster development (utility-first)
- Smaller bundle size (unused styles purged)
- Design consistency (pre-defined palette)
- Mobile-first responsive design
- Dark mode support built-in

### Decision 4: React Router v6 for Routing
**Choice**: Use react-router-dom v6 with route guards for public/private access

**Rationale**:
- Industry standard for React SPAs
- Built-in loader/action pattern (data fetching)
- Nested routes reduce prop drilling
- URL-driven state (bookmarkable, shareable)

### Decision 5: Axios for HTTP Client
**Choice**: Axios (not fetch) for HTTP requests with interceptor hooks for future JWT handling

**Rationale**:
- Automatic JSON serialization
- Global interceptors (add JWT token, handle 401)
- Request/response transformation
- Timeout support
- Simpler error handling than fetch

## Risks / Trade-offs

**[Risk] FSD learning curve**
- Team unfamiliar with FSD conventions
- → Mitigated by: Clear documentation, example features in Auth and Products changes

**[Risk] Too many stores**
- Splitting authStore, cartStore, paymentStore, uiStore could cause fragmentation
- → Accepted because: Separation of concerns makes testing easier; can merge later if needed

**[Risk] Tailwind increases CSS bundle**
- Tailwind utility classes could balloon bundle if not tree-shaken
- → Mitigated by: Using PurgeCSS in build; monitoring bundle size

**[Trade-off] No CSS-in-JS flexibility**
- Dynamic styles are harder with Tailwind (need to use CSS variables or style prop)
- → Accepted because: Use cases rare in Food Store; Tailwind handles 90% of needs

## Migration Plan

1. **Create `frontend/` directory structure** with FSD layers
2. **Install dependencies** (React, Vite, Tailwind, Router, Axios, Zustand) via `package.json`
3. **Set up `frontend/vite.config.ts`** with HMR and build optimization
4. **Configure Tailwind CSS** with design tokens (colors, spacing, fonts)
5. **Create base layouts** (AppLayout, AdminLayout) with sidebar/navbar
6. **Initialize routing** in `frontend/src/app/Router.tsx` with public/private guards
7. **Create Zustand stores** (authStore, cartStore, paymentStore, uiStore)
8. **Set up HTTP client** in `frontend/src/shared/api/client.ts`
9. **Test locally** via `pnpm dev` (should start on `http://localhost:5173`)
10. **Commit** with no breaking changes (green field, only additions)

No rollback needed; this is foundational scaffolding.

## Open Questions

1. **Dark mode implementation?** → Decision: Tailwind's dark mode toggle; authStore tracks preference, saved to localStorage
2. **Component library?** → Decision: Radix UI headless components (better accessibility) + Tailwind for styling, added in future design-system change
3. **Environment variables for API base URL?** → Decision: `.env.local` (dev) and `.env.production` (build); Vite auto-reads
