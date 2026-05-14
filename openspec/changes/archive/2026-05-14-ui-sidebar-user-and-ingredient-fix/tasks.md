# Tasks: ui-sidebar-user-and-ingredient-fix

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300–380 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (3 independent workstreams) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | SidebarFooter component + TopNavbar cleanup | PR 1 | sidebar-user-footer workstream; self-contained |
| 2 | Ingredient sync in ProductFormModal | PR 1 | admin-products workstream; depends on service functions being in same branch |
| 3 | MercadoPago research doc | PR 1 | payment-mercadopago-frontend workstream; independent doc file |

All three units land in the same PR — frontend-only change, no migration risk.

---

## Phase 1: SidebarFooter Component (Workstream 1)

- [x] 1.1 Create `frontend/src/components/layout/SidebarFooter.tsx` — reads `user` from `useAuthStore`, displays avatar (initials fallback with gradient), `user.nombre`, logout button via `useLogout()`. Accepts `isExpanded: boolean` prop to toggle name visibility.
- [x] 1.2 Import and render `<SidebarFooter isExpanded={isExpanded} />` in `Sidebar.tsx` after the closing `</nav>` tag and before the closing `</aside>`. Pass `isExpanded` from the existing state.
- [x] 1.3 Remove user block (div wrapping avatar + name + LogOut button, lines 54–72) from `TopNavbar.tsx`. Keep cart button and brand/logo.
- [x] 1.4 Wrap mobile user avatar/name `<div>` in `TopNavbar` with `<Link>` pointing to role-appropriate profile route (`/cliente/perfil` for CLIENTE, `/admin/usuarios` for ADMIN/PEDIDOS/STOCK). Visible only on `<768px` via `sm:hidden`.

---

## Phase 2: Ingredient Sync — Service Layer (Workstream 2)

- [x] 2.1 Add `addProductIngredient(productoId, ingredienteId, esRemovible)` to `admin-products.service.ts` — POST `/productos/{id}/ingredientes` with `{ ingrediente_id, es_removible }`.
- [x] 2.2 Add `removeProductIngredient(productoId, ingredienteId)` to `admin-products.service.ts` — DELETE `/productos/{productoId}/ingredientes/{ingredienteId}`.

---

## Phase 3: Ingredient Sync — ProductFormModal (Workstream 2 cont.)

- [x] 3.1 Add `originalIngredientes` ref in `ProductFormModal.tsx` — store initial ingredient list loaded from `getProduct()` (after detail loads) to compare against on submit.
- [x] 3.2 Implement `syncIngredientes(original, current)` async function using extracted `diffIngredientes()` utility: diff the two arrays, issue sequential `removeProductIngredient` for removed associations, `addProductIngredient` for added ones, and for `es_removible` toggles (same id, different flag) issue DELETE then POST to trigger backend reactivation.
- [x] 3.3 Wire `syncIngredientes` into `handleSubmit` via `handleUpdateSuccess` callback passed to `useUpdateProduct` — runs after `updateMutation.mutate` completes, before `onClose`. Store `originalIngredientes` from the current `ingredientes` state after detail load.

---

## Phase 4: MercadoPago Research Document (Workstream 3)

- [x] 4.1 Create `docs/mercadopago-checkout-pro-research.md` — document: preference creation flow, webhook IPN format, return URL behavior, notification polling strategy, integration gaps vs current backend. Include date and links to official MercadoPago docs.

---

## Phase 5: Testing

- [x] 5.1 Write RTL test for `SidebarFooter` — assert user name renders, avatar shows, logout button calls `useLogout`, profile link navigates to correct route by role. (9 tests, all pass)
- [x] 5.2 Unit test for `syncIngredientes` diff logic via `diffIngredientes` utility — cover: no changes, add ingredient, remove ingredient, `es_removible` toggle (DELETE→POST sequence). (8 tests, all pass)

---

## Acceptance Criteria Mapping

| # | Criterion | Task(s) | Status |
|---|-----------|---------|--------|
| AC1: User info absent from TopNavbar on desktop | 1.3 | ✅ |
| AC2: SidebarFooter shows avatar + name + logout | 1.1, 1.2 | ✅ |
| AC3: Click sidebar footer → correct profile route | 1.1 | ✅ |
| AC4: Mobile TopNavbar user info clickable → profile | 1.4 | ✅ |
| AC5: Logout clears session + redirects | 1.1 | ✅ |
| AC6: `es_removible` persists after edit + reload | 3.1, 3.2, 3.3 | ✅ |
| AC7: Ingredient add/remove via individual API calls | 2.1, 2.2, 3.2 | ✅ |
| AC8: Basic fields update before ingredient sync | 3.3 | ✅ |
| AC9: Research doc covers preference/webhook/return/polling | 4.1 | ✅ |
| AC10: Research doc dated + links official MP docs | 4.1 | ✅ |
