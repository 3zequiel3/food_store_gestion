## REMOVED Requirements

### Requirement: Tailwind CSS configuration with design tokens

**Reason**: The previous requirement put all tokens directly in `tailwind.config.ts`. The new architecture uses **CSS custom properties** in `index.css` consumed by Tailwind via `var(--token)` (decision D5). This unlocks dark mode without rebuild and aligns with the shadcn/Radix/Vercel pattern.

**Migration**: See `Requirement: Design tokens via CSS custom properties and Tailwind theme` in `openspec/specs/frontend-foundation/spec.md`.

### Requirement: Global styles and CSS reset

**Reason**: Tailwind's base reset is already applied via `@tailwind base;` and font configuration is part of the design token system. A standalone requirement adds noise without enforcing distinct behavior.

**Migration**: Global styles (Tailwind base + body font + background) are implicit in `index.css` and the Tailwind config. If they need explicit spec coverage in the future, they will be re-added under `frontend-foundation`.

### Requirement: Dark mode foundation

**Reason**: Dark mode is **deferred** in this change. The token system leaves `:root` and a `.dark { ... }` placeholder in `index.css`, but no toggle UI, no `uiStore.theme`, and no persistence are introduced. Spec-ing dark mode now would lock in a contract that has no implementation.

**Migration**: When dark mode is actually built (separate change), propose `Requirement: Dark mode toggle and persistence` under `frontend-foundation` (or a new `theme-toggle` capability). The `.dark` placeholder in `index.css` is already in place to make that future change a single-file token addition.

