## ADDED Requirements

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
