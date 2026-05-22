# Delta Spec: Modal Visual Fixes

## Capability
`modal-visual-fixes`

## Requirement: Opaque Modal Surfaces

### Scenario: AddressModal displays with opaque white surface
- **Given** the user opens the AddressModal (add/edit delivery address)
- **When** the modal is rendered
- **Then** the modal surface has a solid white background (`bg-white`)
- **And** the modal has a subtle border (`border border-gray-200`)
- **And** the backdrop overlay dims the background (`bg-black/60 backdrop-blur-sm`)
- **And** the modal content is fully readable regardless of what page is behind it

### Scenario: OrderDetailModal displays with opaque white surface
- **Given** the user opens the OrderDetailModal (view order details)
- **When** the modal is rendered
- **Then** the modal surface has a solid white background (`bg-white`)
- **And** the modal has a subtle border (`border border-gray-200`)
- **And** the backdrop overlay dims the background (`bg-black/60 backdrop-blur-sm`)
- **And** the modal content is fully readable regardless of what page is behind it
- **And** the sticky header is also opaque white (not frosted glass)

### Scenario: PasswordModal displays with opaque white surface
- **Given** the user opens the PasswordModal (change password)
- **When** the modal is rendered
- **Then** the modal surface has a solid white background (`bg-white`)
- **And** the modal content is fully readable regardless of what page is behind it

## Implementation Details

### Components to Update
1. `frontend/src/features/delivery-addresses/components/AddressModal.tsx`
2. `frontend/src/features/orders/components/OrderDetailModal.tsx`
3. `frontend/src/features/user-profile/components/PasswordModal.tsx`

### CSS Changes

**Before (frosted glass — causes grey gradient):**
```
bg-glass backdrop-blur-xl border border-glass-border
```

**After (opaque white — clean surface):**
```
bg-white border border-gray-200
```

**Backdrop overlay (keep unchanged):**
```
bg-black/60 backdrop-blur-sm
```

### Components NOT to Change
- `CartDrawer`: Uses a different pattern (side panel, not modal overlay)
- `CartValidationModal`: Already uses `bg-card` (opaque)
- `MobileMoreDrawer`: Drawer pattern from bottom, glass effect is intentional
