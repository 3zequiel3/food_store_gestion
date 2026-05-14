# Design: UI Sidebar User & Ingredient Fix

## Technical Approach

Three independent frontend workstreams sharing a change: (1) extract user identity from TopNavbar into a SidebarFooter component, (2) wire ingredient sync in ProductFormModal edit mode using existing backend M:N endpoints, (3) produce a MercadoPago research doc. No backend changes required.

## Architecture Decisions

### Decision: SidebarFooter as standalone component

**Choice**: New `SidebarFooter.tsx` component rendered inside `Sidebar.tsx` after the `<nav>` element.
**Alternatives considered**: Inline user block in Sidebar.tsx; keep in TopNavbar and just add Link wrapper.
**Rationale**: Follows project's component-per-concern pattern. Sidebar.tsx is already 262 lines — adding user UI inline would bloat it. Standalone component is independently testable.

### Decision: Ingredient sync strategy — diff-based sequential calls with DELETE-POST for updates

**Choice**: On edit submit, diff `originalIngredientes` vs current `ingredientes` state:
- **Added** (in current, not in original): `POST /productos/{id}/ingredientes`
- **Removed** (in original, not in current): `DELETE /productos/{id}/ingredientes/{ingId}`
- **Changed `es_removible`** (same id, different flag): `DELETE` then `POST` — backend reactivates soft-deleted pivot rows and sets the new `es_removible` value.

**Alternatives considered**: Re-POST all ingredients (409 on active associations — `ConflictError` in `repository.py:407`). Bulk replace endpoint (doesn't exist).
**Rationale**: Backend `add_ingrediente` raises `ConflictError` for active pivot rows. The DELETE→POST pattern uses the built-in reactivation logic (`repository.py:408-413`) which clears `eliminado_en` and updates `es_removible`. Sequential calls acceptable for small N (typically <10 ingredients).

### Decision: Mobile profile navigation via Link wrapper

**Choice**: Wrap the existing user avatar/name `<div>` in TopNavbar with a `<Link to={profileRoute}>`.
**Alternatives considered**: Remove user info from mobile entirely; add a separate profile button.
**Rationale**: Minimal change, same visual footprint, preserves mobile UX. Profile route determined by same role logic as sidebar.

## Data Flow

### SidebarFooter
```
useAuthStore → user object
  ├─ user.nombre → display
  ├─ hasRole('ADMIN'|'PEDIDOS'|'STOCK') → route = /admin/usuarios
  └─ else → route = /cliente/perfil

useLogout → mutate() → clearSession + redirect
```

### Ingredient Sync (edit mode)
```
handleSubmit
  ├─ 1. updateMutation.mutate(basicFields) → PUT /productos/{id}
  ├─ 2. await syncIngredientes(producto.id, original, current)
  │     ├─ removed = original - current → DELETE /productos/{id}/ingredientes/{ingId}
  │     ├─ added = current - original → POST /productos/{id}/ingredientes {ingrediente_id, es_removible}
  │     └─ es_removible changed (same id) → DELETE then POST (reactivation)
  ├─ 3. queryClient.invalidate(['products'])
  └─ 4. onClose()
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components/layout/SidebarFooter.tsx` | Create | User avatar, name, profile link, logout button. Reads from `useAuthStore` + `useLogout`. |
| `frontend/src/components/layout/Sidebar.tsx` | Modify | Import + render `<SidebarFooter>` after `<nav>`, inside `<aside>`. Pass `isExpanded` prop. |
| `frontend/src/components/layout/TopNavbar.tsx` | Modify | Remove user avatar/name/logout block (lines 54-72). Keep cart button. Add `<Link>` wrapper for mobile profile nav. |
| `frontend/src/features/products/components/admin/ProductFormModal.tsx` | Modify | Add `originalIngredientes` ref, `syncIngredientes()` async function after basic field update, wire into `handleSubmit`. |
| `frontend/src/features/products/services/admin-products.service.ts` | Modify | Add `addProductIngredient()` and `removeProductIngredient()` service functions using `ENDPOINTS.productos.ingredientes` and `ENDPOINTS.productos.ingredienteDelete`. |
| `docs/mercadopago-checkout-pro-research.md` | Create | Research doc: preference creation, webhook IPN format, return URLs, notification polling. |

## Interfaces / Contracts

```typescript
// SidebarFooter props
interface SidebarFooterProps {
  isExpanded: boolean;  // controls name visibility (collapsed = avatar only)
}

// New service functions
async function addProductIngredient(
  productoId: number,
  ingredienteId: number,
  esRemovible: boolean
): Promise<IngredienteAsociadoRead>;

async function removeProductIngredient(
  productoId: number,
  ingredienteId: number
): Promise<void>;
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | SidebarFooter renders user info, routes correctly per role | React Testing Library + mocked authStore |
| Unit | Ingredient sync diff logic (add/remove/update detection) | Pure function test with mock data |
| Integration | ProductFormModal edit mode persists es_removible | Mock API calls, verify DELETE→POST sequence for changed flags |
| Visual | Sidebar footer alignment in collapsed vs expanded states | Manual check (collapsed: icon only, expanded: icon + name) |

## Migration / Rollout

No migration required. Frontend-only change. Rollback = revert commit.

## Open Questions

- [ ] Should SidebarFooter show user email in addition to name? Current TopNavbar shows `user.nombre` only.
