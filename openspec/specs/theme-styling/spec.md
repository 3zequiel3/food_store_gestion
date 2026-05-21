# theme-styling Specification

## Purpose
TBD - created by archiving change setup-frontend-core. Update Purpose after archive.
## Requirements
### Requirement: Tailwind CSS configuration with design tokens
The system SHALL configure Tailwind CSS with custom design tokens for colors, spacing, typography, and breakpoints consistent with the Food Store brand.

#### Scenario: Tailwind processes utility classes
- **WHEN** a component uses Tailwind classes like `bg-primary text-white p-4`
- **THEN** the compiled CSS includes only the used classes (tree-shaken)

#### Scenario: Design tokens are defined
- **WHEN** the developer needs a brand color
- **THEN** custom colors are available: `primary`, `secondary`, `accent`, `success`, `warning`, `error` in `tailwind.config.ts`

#### Scenario: Responsive breakpoints work
- **WHEN** a component uses `md:flex lg:grid`
- **THEN** the layout adapts to screen size following mobile-first design

### Requirement: Global styles and CSS reset
The system SHALL provide global CSS with Tailwind's base layer, font configuration, and consistent default styles.

#### Scenario: Global styles are applied
- **WHEN** the application loads
- **THEN** Tailwind's base reset is applied and custom global styles (body font, background) are set

#### Scenario: Custom font is loaded
- **WHEN** the application renders text
- **THEN** the configured font family (Inter or system font stack) is used

### Requirement: Dark mode foundation
The system SHALL support dark mode toggling using Tailwind's `dark:` variant with class-based strategy.

#### Scenario: Dark mode can be toggled
- **WHEN** a user toggles dark mode
- **THEN** the `dark` class is added to the `<html>` element and all `dark:` variants are applied

#### Scenario: Dark mode preference is persisted
- **WHEN** a user selects dark mode
- **THEN** the preference is saved to localStorage and restored on next visit

### Requirement: Glass surface tokens
The system SHALL define `--color-glass`, `--color-glass-border`, and `--color-chrome-glass` design tokens in `index.css` using OKLCH with alpha transparency. The glass tokens SHALL have light mode overrides in `:root.light`.

#### Scenario: Glass token resolves to semi-transparent OKLCH
- **WHEN** inspecting `--color-glass` in dark mode
- **THEN** the value is `oklch(0.20 0.08 273 / 0.4)` (semi-transparent indigo)

### Requirement: Brand gradient
The system SHALL define a `--gradient-brand` value transitioning from primary to secondary. The gradient SHALL be used in hero sections and decorative elements.

#### Scenario: Gradient renders correctly
- **WHEN** using `bg-gradient-to-br from-primary via-primary/80 to-secondary`
- **THEN** the gradient transitions smoothly from `#2F2FE4` toward `#162E93`

### Requirement: Corrected OKLCH palette
The system SHALL correct the OKLCH values in `@theme` to precisely match the hex palette from `docs/colores.md`. Each token SHALL have a verified dark and light value.

#### Scenario: Background token matches #080616
- **WHEN** computing the OKLCH value for `--color-background`
- **THEN** the perceived color is `#080616` (currently `oklch(0.06 0.025 274)`)

### Requirement: Glass chrome surfaces
Layout chrome (TopNavbar, Sidebar, BottomNav) SHALL use `--color-chrome-glass` with `backdrop-blur-xl` for a glassmorphism effect. The chrome glass SHALL be more opaque than card glass for readability.

#### Scenario: Navbar has glass effect
- **WHEN** rendering TopNavbar
- **THEN** it has `backdrop-blur-xl` and `bg-chrome-glass` tokens applied

### Requirement: Micro-interaction tokens
The system SHALL define transition tokens for micro-interactions: hover lift (translateY -2px + shadow increase), smooth color transitions (150ms ease-out), and shimmer animation for skeletons.

#### Scenario: Card has hover lift
- **WHEN** hovering an interactive card
- **THEN** the card translates up 2px and shadow increases

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
