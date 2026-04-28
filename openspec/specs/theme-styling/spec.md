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

