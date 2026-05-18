# Proposal: Public Landing Page

## Intent

The app has NO public-facing page. `/` redirects unauthenticated users to `/login` and authenticated users to `/admin` or `/cliente`. This means potential customers cannot see the business, products, or offerings without creating an account first. We need a public landing page at `/` that is accessible to everyone — authenticated or not — to showcase the business, featured products, and drive conversions.

## Scope

### In Scope
- New `LandingPage` component with Hero, Categories, Featured Products, Info, and Footer sections
- Route `/` moved OUTSIDE `PrivateRoute` guard — accessible to all users
- `LandingProductCard` — simplified product card without cart dependency (CTA: "Ver producto" → `/cliente/catalogo/:id`)
- Authenticated users visiting `/` see the landing page (no redirect away)
- Reuse existing `useProducts()`, `useCategorias()`, `ProductImage`, `Button`, `Card`, `Badge` components

### Out of Scope
- SEO optimization (meta tags, SSR, Open Graph)
- Public catalog browsing with filters (belongs to `products-frontend-catalog`)
- Landing page CMS or admin-configurable content
- A/B testing or analytics integration
- Redesigning existing `ProductCard` — new `LandingProductCard` is a separate component

## Capabilities

### New Capabilities
- `public-landing-page`: Public-facing landing page at `/` with business info, category showcase, featured products grid, and CTAs. Accessible without authentication. Authenticated users are NOT redirected away.

### Modified Capabilities
- `routing-guards`: Route `/` behavior changes — no longer inside `PrivateRoute`. Authenticated users visiting `/` stay on the landing page instead of being redirected to `/admin` or `/cliente`. The "Public route access" requirement needs updating to include `/` as a public route.

## Approach

1. **Route restructuring**: Add `<Route path="/" element={<LandingPage />} />` at the top level of `Routes`, BEFORE `PublicRoute` and `PrivateRoute`. Remove `/` from inside `PrivateRoute`. `RootRedirect` stays but moves to a different path (e.g., `/dashboard`) or is replaced by role-aware redirect logic in the navbar.

2. **LandingPage component**: Single page at `frontend/src/pages/LandingPage.tsx` with its own layout (no `AppLayout` wrapper). Sections:
   - **Hero**: Business name, tagline, CTA buttons ("Ver menú" → `/cliente/catalogo`, "Ingresar" → `/login`)
   - **Categories**: Grid of category cards using `useCategorias()`, each links to `/cliente/catalogo?categoria=<id>`
   - **Featured Products**: Grid of 6-8 products using `useProducts({ disponible: true })` with slice, each rendered as `LandingProductCard`
   - **Info Section**: Delivery info, horarios, contacto
   - **Footer**: Links to login/register, copyright

3. **LandingProductCard**: New component at `frontend/src/features/products/components/LandingProductCard.tsx`. Shows image, name, price, availability badge. CTA button navigates to `/cliente/catalogo/:id` (which is behind auth guard — unauthenticated users will be redirected to login). No cart dependency.

4. **Auth behavior**: `TopNavbar` already handles auth state. If reused on landing, it shows login/register links when unauthenticated, cart/profile when authenticated. Alternatively, landing has its own simpler header.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/router/AppRoute.tsx` | Modified | Add `/` route outside guards, adjust `RootRedirect` placement |
| `frontend/src/pages/LandingPage.tsx` | New | Landing page with Hero, Categories, Products, Info, Footer |
| `frontend/src/features/products/components/LandingProductCard.tsx` | New | Simplified product card without cart dependency |
| `frontend/src/components/layout/TopNavbar.tsx` | Modified (optional) | Handle public route context if reused on landing |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `RootRedirect` logic breaks if `/` is no longer inside `PrivateRoute` | Medium | Move role-aware redirect to a `/dashboard` route or integrate into TopNavbar |
| `LandingProductCard` diverges from `ProductCard` over time | Low | Extract shared sub-components (image, price formatting) to `shared/` |
| Unauthenticated users click "Ver producto" and hit login redirect | Medium | Acceptable behavior — drives registration. Add clear messaging on login page |
| Landing page layout conflicts with existing design tokens | Low | Use existing `--color-*` tokens and `Card`/`Button` components |

## Rollback Plan

1. Revert the route change in `AppRoute.tsx` — move `/` back inside `PrivateRoute` with `RootRedirect`.
2. Delete `LandingPage.tsx` and `LandingProductCard.tsx`.
3. No database or API changes — purely frontend, so rollback is file-level only.

## Dependencies

- `frontend-rebuild-on-feature-first` must be archived (routing foundation, UI components must exist)
- `products-frontend-catalog` NOT required — landing only needs `useProducts()` hook and `ProductImage`, which already exist

## Success Criteria

- [ ] `/` renders the landing page for unauthenticated users (no redirect to `/login`)
- [ ] `/` renders the landing page for authenticated users (no redirect to `/admin` or `/cliente`)
- [ ] Featured products load from `GET /productos/?disponible=true` and display correctly
- [ ] Categories load from `GET /categorias/` and display as clickable cards
- [ ] "Ver menú" CTA navigates to `/cliente/catalogo` (auth required)
- [ ] "Ingresar" CTA navigates to `/login`
- [ ] `LandingProductCard` has zero imports from `cartStore`
