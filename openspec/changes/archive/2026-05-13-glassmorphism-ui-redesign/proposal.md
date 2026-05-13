## Why

The current frontend UI is functional but visually flat — no personality, no visual hierarchy, no modern design language. All components use raw utility classes with repeated patterns (no shared primitives), cards are flat surfaces with borders, and there are zero micro-interactions. A complete visual redesign using glassmorphism will give the app a distinctive, modern, polished identity that makes it stand out.

## What Changes

- Add glass-specific design tokens to `index.css` (glass surfaces, borders, chromatic tokens)
- Create shared UI primitives in `components/ui/`: Button, Input, Card, Badge
- Refactor ALL existing components to use the new UI primitives — no more raw className patterns
- Apply glassmorphism surfaces across layout (navbar, sidebar, bottom nav, drawers)
- Redesign auth pages with glass cards and gradient backgrounds
- Enhance product catalog cards with hover animations and glass overlays
- Refactor OrderStatusBadge to use semantic design tokens instead of hardcoded Tailwind colors
- Add micro-interactions (hover lift, smooth transitions, shimmer skeletons)
- Fix OKLCH color values to match the brand palette from `docs/colores.md`
- **No business logic changes** — presentation layer only

## Capabilities

### New Capabilities
- `ui-primitives`: Shared component library (Button, Input, Card, Badge) with variants and design tokens
- `glassmorphism-theme`: Design system tokens for glass surfaces, gradients, and micro-interactions

### Modified Capabilities
- (none — no existing spec changes, this is visual-only)

## Impact

- `frontend/src/index.css` — refactor tokens, add glass/gradient/chromatic tokens
- `frontend/src/components/ui/` — new directory with 4 shared primitives
- `frontend/src/components/layout/*` — visual refactor of 6 layout components
- `frontend/src/features/*/components/*` — visual refactor of ~25 feature components
- `frontend/src/pages/*` — visual refactor of 10 page components
- No changes to: hooks, stores, services, schemas, types, router, tests
