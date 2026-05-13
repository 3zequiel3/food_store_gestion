## Context

Current frontend uses Tailwind v4 with a dark-first design system defined in `index.css`. The design tokens exist but need correction (OKLCH values don't match the brand palette from `docs/colores.md`). All components use raw utility classes with massive repetition — no shared UI primitives. The visual design is flat, with zero glassmorphism, gradients, or micro-interactions.

## Goals / Non-Goals

**Goals:**
- Correct OKLCH color values to match `#2F2FE4`, `#162E93`, `#1A1953`, `#080616`
- Add glassmorphism design tokens (glass surfaces, borders, chrome glass, brand gradients)
- Create reusable UI primitives: `Button`, `Input`, `Card`, `Badge`
- Apply glassmorphism across all layout components (TopNavbar, Sidebar, BottomNav, CartDrawer)
- Refactor feature components to use primitives and glass surfaces
- Redesign auth pages with glass cards and radial gradient backgrounds
- Add micro-interactions: hover lift, smooth transitions, shimmer skeleton
- Ensure light mode also works with glass tokens

**Non-Goals:**
- No business logic changes (hooks, stores, services, schemas, types, router, tests)
- No new features or functionality
- No changes to the backend
- No re-architecture of component hierarchy

## Decisions

### 1. Glassmorphism via CSS custom properties, not utility classes
- **Decision**: Add `--color-glass`, `--color-glass-border`, `--color-chrome-glass` to `@theme` in `index.css`, plus a `gradient-brand` via `@media`-safe approach
- **Rationale**: Tailwind v4 doesn't natively support `backdrop-filter` as a utility that composes with custom properties. Define the glass surfaces as reusable tokens and use `backdrop-blur-xl` + the glass color in each component.
- **Alternatives considered**: Creating a custom Tailwind plugin → overkill for this scope

### 2. UI primitives in `components/ui/`, not a separate package
- **Decision**: Create `Button`, `Input`, `Card`, `Badge` as simple React components with `cva` (class-variance-authority) or manual variant maps
- **Rationale**: No external component library — these are thin wrappers over Tailwind classes. Keeping them in-tree avoids npm dependency bloat.
- **Note**: Since the project doesn't have `cva`, we'll use a simple helper pattern with variant objects

### 3. Progressive enhancement, not rewrite
- **Decision**: Each file is edited in place. Components get refactored one by one, starting with the design system, then primitives, then layout, then features.
- **Rationale**: The project already works. A ground-up rewrite would break everything at once and make debugging impossible.
- **Tradeoff**: Some intermediate states will have mixed styles, but each phase leaves the app functional.

### 4. Browser support: `backdrop-filter`
- **Decision**: Use `backdrop-filter` with `-webkit-backdrop-filter` fallback
- **Rationale**: All modern browsers support it. Safari needs the `-webkit-` prefix.
- **Risk**: Very old browsers (pre-2020) will show solid backgrounds instead of glass — acceptable degradation.

## Risks / Trade-offs

- **[Performance]** Multiple `backdrop-blur` layers can cause repaint cost → Mitigation: limit glass surfaces to chrome (navbar, sidebar) and cards; avoid stacking glass on glass
- **[Light mode]** Glass surfaces on light backgrounds may look muddy → Mitigation: adjust glass opacity in `:root.light` overrides (higher opacity, lower blur)
- **[Consistency]** Replacing raw className patterns with primitives may miss edge cases → Mitigation: verify each component visually after refactor
- **[Scope creep]** "While we're at it" syndrome → Mitigation: strictly non-goals documented, no business logic changes
