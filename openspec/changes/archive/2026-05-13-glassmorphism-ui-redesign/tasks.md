## 1. Design Tokens — index.css

- [x] 1.1 Correct OKLCH values for background, card, primary, secondary to match brand palette
- [x] 1.2 Add `--color-glass`, `--color-glass-border`, `--color-chrome-glass` tokens with alpha
- [x] 1.3 Add `--gradient-brand` and `--gradient-hero` tokens
- [x] 1.4 Add `--animate-shimmer` keyframe for skeleton loading
- [x] 1.5 Update `:root.light` overrides with glass token equivalents

## 2. UI Primitives

- [x] 2.1 Create `Button` component with variants (primary, secondary, ghost, destructive, outline), sizes (sm, md, lg), and loading state
- [x] 2.2 Create `Input` component with label, error, and icon slots
- [x] 2.3 Create `Card` component with variants (elevated, outlined, interactive) and glass surface
- [x] 2.4 Create `Badge` component with semantic variants (success, warning, destructive, info, neutral)

## 3. Layout Refactor

- [x] 3.1 TopNavbar: glass chrome effect, logo with gradient, refined spacing
- [x] 3.2 Sidebar: glass effect, active indicator, better transitions
- [x] 3.3 BottomNav: active bar indicator, better active state
- [x] 3.4 CartDrawer: glass surface, header gradient, refined item list
- [x] 3.5 MobileMoreDrawer: glass surface consistency

## 4. Auth Pages

- [x] 4.1 LoginPage: radial gradient background, glass card, refined typography
- [x] 4.2 LoginForm: replace raw inputs with Button/Input primitives
- [x] 4.3 RegisterPage: same treatment as LoginPage
- [x] 4.4 RegisterForm: replace raw inputs with Button/Input primitives

## 5. Catalog & Products

- [x] 5.1 ProductCard: glass elevated card, hover lift, image glass overlay
- [x] 5.2 ProductCardSkeleton: shimmer animation instead of animate-pulse
- [x] 5.3 ProductGrid: refined gap and responsive layout
- [x] 5.4 SearchBar, CategoryFilter, AllergenFilter: glass surfaces
- [x] 5.5 ActiveFilterChips: better chip styling with glass
- [x] 5.6 Pagination: glass surface for controls

## 6. Orders & Checkout

- [x] 6.1 OrderStatusBadge: replace hardcoded colors with Badge component
- [x] 6.2 OrderCard: glass card with refined hierarchy
- [x] 6.3 OrderCardSkeleton: shimmer animation
- [x] 6.4 OrderDetailModal: glass surface
- [x] 6.5 OrderTimeline: refined visual timeline
- [x] 6.6 CheckoutPage: glass surfaces for sections, step indicators
- [x] 6.7 AddressSelector, PaymentMethodSelector: glass cards
- [x] 6.8 OrderSummary: glass surface with refined total display

## 7. Profile, Addresses & Admin

- [x] 7.1 ProfileForm: glass card, primitives
- [x] 7.2 PasswordModal: glass surface
- [x] 7.3 AddressCard: glass card
- [x] 7.4 AddressModal: glass surface
- [x] 7.5 Error pages (404, 403, 401): gradient backgrounds, glass cards
- [x] 7.6 AdminLayout, PedidosAdminPage: glass consistency

## 8. Cleanup

- [x] 8.1 Verify no hardcoded hex colors in components
- [x] 8.2 Verify light mode renders correctly
- [x] 8.3 Remove any unused className patterns after refactor
