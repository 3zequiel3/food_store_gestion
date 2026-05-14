# Proposal: UI Sidebar User & Ingredient Fix

## Intent

Three independent frontend improvements:
1. **User info misplaced** — logged-in user avatar/name/logout lives in `TopNavbar` (header) instead of the sidebar where navigation belongs. The sidebar footer is the standard pattern for user identity in admin/client dashboards.
2. **`es_removible` not persisting** — when an admin assigns an ingredient to a product, the `es_removible` toggle works visually but is NOT synced to the backend in edit mode. The `ProductFormModal` handleSubmit for edit only sends basic fields (nombre, precio, stock, disponible) — ingredient sync is deferred ("Note: category/ingredient/image sync would happen via separate endpoints").
3. **MercadoPago Checkout Pro integration undocumented** — backend endpoints exist but frontend integration state is unclear. A research doc will unblock future payment work.

## Scope

### In Scope
- Extract user info from `TopNavbar.tsx` into a new `SidebarFooter` component
- Add footer area to `Sidebar.tsx` (desktop) with clickable navigation to profile
- Make mobile TopNavbar user info clickable to navigate to profile (`/cliente/perfil` for clients, `/admin/usuarios` for admin self-edit)
- Fix `es_removible` persistence: wire ingredient sync in edit mode via `PUT /api/v1/productos/{id}/ingredientes/{ingId}` endpoint
- Research document: MercadoPago Checkout Pro integration findings (no code changes)

### Out of Scope
- Backend changes (payment endpoints already exist)
- Actual MercadoPago SDK integration (research only)
- Mobile sidebar redesign (mobile uses TopNavbar, which stays visible)
- Other product form fields in edit mode (categories, images — separate changes)

## Capabilities

### New Capabilities
- `sidebar-user-footer`: Sidebar footer with user identity, profile navigation, and logout action

### Modified Capabilities
- `admin-products`: Edit mode now syncs ingredient assignments (including `es_removible`) to backend, not just basic fields
- `payment-mercadopago-frontend`: Research findings document current integration state and gaps (no spec-level behavior change yet)

## Approach

1. Create `SidebarFooter` component: reads user from `useAuthStore`, renders avatar + name + clickable area. Routes to `/cliente/perfil` (client) or `/admin/usuarios` (admin). Includes logout button.
2. Remove user info block from `TopNavbar.tsx` (keep cart button for clients).
3. Insert `SidebarFooter` at bottom of `Sidebar.tsx` nav, styled as a fixed footer area within the aside.
4. Wrap mobile TopNavbar user section in a `<button>` or `<Link>` that navigates to profile.
5. Fix edit-mode ingredient sync: after `updateMutation.mutate()` for basic fields, iterate ingredient changes and call the individual ingredient association endpoints (`PUT /api/v1/productos/{id}/ingredientes/{ingId}` for existing, `POST` for new, `DELETE` for removed).
6. Write `docs/mercadopago-checkout-pro-research.md` with findings on webhook format, preference creation, return URLs, and notification handling.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/components/layout/TopNavbar.tsx` | Modified | Remove user avatar/name/logout block; keep cart + brand |
| `frontend/src/components/layout/Sidebar.tsx` | Modified | Add `SidebarFooter` at bottom of aside |
| `frontend/src/components/layout/SidebarFooter.tsx` | New | User identity, profile nav, logout |
| `frontend/src/features/products/components/admin/ProductFormModal.tsx` | Modified | Wire ingredient sync in edit mode (add/update/remove via API) |
| `docs/mercadopago-checkout-pro-research.md` | New | Research document for Checkout Pro integration |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Mobile layout broken after TopNavbar change | Low | User info becomes clickable link, same visual footprint |
| Ingredient sync in edit mode races with basic field update | Medium | Sequence: basic fields first, then ingredient associations; show loading state |
| Admin profile route ambiguity | Low | Use `/admin/usuarios` for self-edit (admin can find themselves in the list) |
| Research doc becomes stale if MP changes API | Medium | Document date + link to official MP docs for reference |

## Rollback Plan

1. Revert the commit: `git revert HEAD` — restores TopNavbar user info, removes SidebarFooter
2. Revert ProductFormModal changes: edit mode returns to basic-fields-only behavior
3. Delete research doc: `rm docs/mercadopago-checkout-pro-research.md`

## Dependencies

- None — all work is frontend-only and uses existing backend endpoints

## Success Criteria

- [ ] User info no longer appears in TopNavbar (desktop); appears only in Sidebar footer
- [ ] Clicking user info in sidebar navigates to correct profile page (client or admin)
- [ ] Mobile TopNavbar user info is clickable and navigates to profile
- [ ] Admin can toggle `es_removible` on an ingredient in edit mode and the value persists after reload
- [ ] Research document covers: preference creation flow, webhook IPN format, return URL behavior, notification polling
