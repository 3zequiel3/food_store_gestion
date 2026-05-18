# public-landing-page Specification

## Purpose
Provide a public-facing landing page at `/` accessible to all users (authenticated or not) to showcase the business, featured products, categories, and drive conversions.

## Requirements

### Requirement: Public Landing Page Route
The route `/` SHALL serve a public landing page accessible to both authenticated and unauthenticated users. No redirect SHALL occur based on auth state.

#### Scenario: Unauthenticated visitor sees landing page
- **GIVEN** a user is not authenticated
- **WHEN** they visit `/`
- **THEN** they see the full landing page with Hero, Categories, Featured Products, Info, and Footer sections
- **AND** the "Ver menú" CTA links to `/login`

#### Scenario: Authenticated user sees landing page
- **GIVEN** a user is authenticated
- **WHEN** they visit `/`
- **THEN** they see the same landing page
- **AND** the "Ver menú" CTA links to `/cliente/catalogo`
- **AND** the TopNavbar shows their cart count and profile

#### Scenario: No role-based redirect at `/`
- **GIVEN** any user visits `/`
- **WHEN** they land on the page
- **THEN** they are NOT redirected to `/admin` or `/cliente`
- **AND** the page renders immediately

### Requirement: Landing Page Sections
The landing page SHALL render distinct visual sections with responsive layout.

#### Scenario: Hero section
- **GIVEN** the landing page is rendered
- **WHEN** the user views the top of the page
- **THEN** they see a hero with: business name "Food Store", tagline, and two CTA buttons ("Ver menú" and "Ingresar")
- **AND** the hero uses the primary color scheme and glassmorphism card style

#### Scenario: Categories section
- **GIVEN** the landing page is rendered
- **WHEN** categories are available from the API
- **THEN** a grid of category cards is displayed (up to 6)
- **AND** each card shows the category name and an icon
- **AND** clicking a category navigates to the catalog (login for unauth, `/cliente/catalogo` for auth)

#### Scenario: Featured Products section
- **GIVEN** the landing page is rendered
- **WHEN** products are available from the API
- **THEN** a grid of up to 8 featured products is displayed
- **AND** each product uses `LandingProductCard` (no cart dependency)
- **AND** each card shows: product image, name, price, and "Ver más" button
- **AND** clicking "Ver más" navigates to login (unauth) or `/cliente/catalogo/:id` (auth)

#### Scenario: Loading and error states
- **GIVEN** the API calls are in progress
- **WHEN** data hasn't loaded yet
- **THEN** skeleton loaders are shown for categories and products
- **AND** if the API fails, an error message with a retry button is shown

### Requirement: LandingProductCard Component
A simplified product card for public display without cart functionality SHALL be implemented.

#### Scenario: Card displays product info
- **GIVEN** a `LandingProductCard` receives a `ProductoRead` object
- **WHEN** rendered
- **THEN** it shows: product image (via `ProductImage`), name, price, and description (truncated)
- **AND** it does NOT import or use `useCartStore`
- **AND** it does NOT show "Agregar al carrito" button

#### Scenario: Card navigation
- **GIVEN** the user clicks "Ver más" on a card
- **WHEN** the user is authenticated
- **THEN** they navigate to `/cliente/catalogo/:id`
- **WHEN** the user is NOT authenticated
- **THEN** they navigate to `/login`

### Requirement: Responsive Design
The landing page SHALL work on mobile and desktop viewports.

#### Scenario: Mobile layout
- **GIVEN** viewport width < 768px
- **WHEN** the landing page is viewed
- **THEN** sections stack vertically
- **AND** product grid is 1-2 columns
- **AND** category grid is 2 columns

#### Scenario: Desktop layout
- **GIVEN** viewport width >= 768px
- **WHEN** the landing page is viewed
- **THEN** sections use wider layouts
- **AND** product grid is 3-4 columns
- **AND** category grid is 3-4 columns

### Requirement: Hero Section visual hierarchy
The Hero section SHALL use an asymmetric two-column layout on desktop (`lg:` breakpoint and above) with a stacked single-column layout on mobile. The left column SHALL contain the business name, tagline, and primary CTAs. The right column SHALL contain a visual element (animated CSS shapes, SVG illustration, or photographic asset — final asset decided per design D2). The section SHALL NOT use the previous centered glass card pattern.

#### Scenario: Desktop hero layout
- **GIVEN** the viewport width is `>= 1024px`
- **WHEN** the user views the landing page
- **THEN** the hero displays the copy block (title, tagline, CTAs) on the left side
- **AND** displays the visual element on the right side
- **AND** the two columns are visually balanced but asymmetric (not 50/50; copy column wider)

#### Scenario: Mobile hero layout
- **GIVEN** the viewport width is `< 1024px`
- **WHEN** the user views the landing page
- **THEN** the copy block stacks on top
- **AND** the visual element stacks below
- **AND** both columns span the full width

#### Scenario: Hero is not a centered glass card
- **GIVEN** the landing page is rendered
- **WHEN** the user views the hero
- **THEN** the hero does NOT render a single `Card variant="glass" inline-block` centered as the primary content container
- **AND** the hero uses full-bleed background

### Requirement: Stats Bar Section
The landing page SHALL render a Stats Bar section between the Hero and the Categories sections. The bar SHALL display 3 or 4 placeholder metrics (e.g., total orders, average delivery time, freshness commitment, average rating) intended as social proof.

#### Scenario: Stats bar renders below hero
- **GIVEN** the landing page is rendered
- **WHEN** the user scrolls below the hero
- **THEN** they see a stats bar with 3 or 4 metrics displayed in a horizontal strip
- **AND** the bar uses distinct visual treatment from the Hero and Categories sections (different background or border treatment)

#### Scenario: Stats bar responsive layout
- **GIVEN** the viewport width is `>= 640px`
- **WHEN** the stats bar renders
- **THEN** the metrics are displayed in a single row with equal-width columns
- **WHEN** the viewport width is `< 640px`
- **THEN** the metrics are displayed in a 2x2 grid

#### Scenario: Stats are placeholder values marked for replacement
- **GIVEN** the stats bar renders
- **WHEN** the source code is inspected
- **THEN** the stats values are hardcoded with a `TODO(landing-stats)` comment indicating they SHALL be replaced with real backend metrics in a future change

### Requirement: How It Works Section
The landing page SHALL render a "How It Works" section that explains the customer flow in 3 numbered steps (e.g., "Elegí → Pagá → Recibí"). Each step SHALL display a number, an icon, a title, and a short description.

#### Scenario: How It Works renders 3 steps
- **GIVEN** the landing page is rendered
- **WHEN** the user views the How It Works section
- **THEN** they see exactly 3 step cards
- **AND** each card displays: a step number (1, 2, 3), an icon, a title, and a description

#### Scenario: How It Works replaces the previous Info section
- **GIVEN** the landing page is rendered
- **WHEN** the user inspects the page composition
- **THEN** the previous "¿Por qué elegirnos?" Info section is replaced by the How It Works section
- **AND** the page does NOT render both sections simultaneously

#### Scenario: How It Works desktop layout
- **GIVEN** the viewport width is `>= 768px`
- **WHEN** the section renders
- **THEN** the 3 step cards are displayed in a single row

#### Scenario: How It Works mobile layout
- **GIVEN** the viewport width is `< 768px`
- **WHEN** the section renders
- **THEN** the 3 step cards stack vertically

### Requirement: Footer with four content columns
The Footer SHALL render four distinct content sections (e.g., Compañía, Ayuda, Contacto, Redes) in a responsive grid. The Footer SHALL NOT be a single-row navigation strip with only auth links.

#### Scenario: Footer renders four columns on desktop
- **GIVEN** the viewport width is `>= 1024px`
- **WHEN** the user scrolls to the footer
- **THEN** they see four labeled columns of links/content
- **AND** a copyright row is displayed below the columns

#### Scenario: Footer responsive collapse
- **GIVEN** the viewport width is `< 1024px` and `>= 640px`
- **WHEN** the footer renders
- **THEN** the four columns collapse to a 2x2 grid
- **WHEN** the viewport width is `< 640px`
- **THEN** all columns stack vertically

#### Scenario: Footer columns are semantically navigable
- **GIVEN** the footer renders
- **WHEN** a screen reader user navigates the page
- **THEN** each column is wrapped in a `<nav>` element with an `aria-label` describing the column's purpose

### Requirement: LandingProductCard badges
`LandingProductCard` SHALL display contextual badges over the product image when the corresponding `ProductoRead` fields are present. Supported badges include: "Nuevo" (when `producto.created_at` indicates a recent product, if available), "Destacado" (when `producto.destacado === true`, if the field exists), and "Sin stock" (when `producto.disponible === false`). If a field is not present in `ProductoRead`, the corresponding badge SHALL be omitted silently.

#### Scenario: Product with destacado flag shows Destacado badge
- **GIVEN** a `ProductoRead` object has `destacado: true`
- **WHEN** `LandingProductCard` renders it
- **THEN** a "Destacado" badge is visible over the product image area

#### Scenario: Product without destacado flag shows no Destacado badge
- **GIVEN** a `ProductoRead` object has `destacado: false` or the field is absent
- **WHEN** `LandingProductCard` renders it
- **THEN** no "Destacado" badge is displayed

#### Scenario: Badges are accessible to screen readers
- **GIVEN** a badge is rendered
- **WHEN** a screen reader navigates to it
- **THEN** the badge exposes an `aria-label` describing the state (e.g., "Producto destacado")

### Requirement: LandingProductCard hover interaction
`LandingProductCard` SHALL display a visual hover affordance over the product image area beyond a simple `translate-y` lift. The card SHALL apply an image zoom effect (scale transform) and a card-level lift with shadow on hover. The interaction SHALL be disabled when `prefers-reduced-motion: reduce` is active.

#### Scenario: Card hover shows image zoom and lift
- **GIVEN** a `LandingProductCard` is rendered
- **WHEN** the user hovers over the card
- **THEN** the product image scales up slightly within the image container
- **AND** the card lifts with an increased shadow
- **AND** the transition is smooth (not instant)

#### Scenario: Reduced motion disables hover animations
- **GIVEN** the user's system has `prefers-reduced-motion: reduce` enabled
- **WHEN** they hover over a `LandingProductCard`
- **THEN** no scale or lift animation occurs
- **AND** the card remains visually static

### Requirement: Motion design with reduced-motion respect
The landing page SHALL implement scroll-triggered fade-in animations on sections and staggered reveal on grid items using CSS transitions and the `IntersectionObserver` Web API. All motion SHALL be disabled when the user's system reports `prefers-reduced-motion: reduce`.

#### Scenario: Sections fade in on scroll
- **GIVEN** the user lands on the page with normal motion preferences
- **WHEN** they scroll a section into the viewport
- **THEN** the section transitions from `opacity: 0` and slight translateY offset to its final position
- **AND** the transition uses transform and opacity properties only (no layout-triggering properties)

#### Scenario: Grid items appear with stagger
- **GIVEN** a grid section (Categories, FeaturedProducts, HowItWorks) enters the viewport
- **WHEN** the items reveal
- **THEN** each item's appearance is delayed by an incremental amount (stagger)
- **AND** the overall stagger sequence completes within 1 second of the first item appearing

#### Scenario: Reduced motion disables all scroll animations
- **GIVEN** the user's system has `prefers-reduced-motion: reduce` enabled
- **WHEN** the landing page renders
- **THEN** all sections and grid items are visible immediately at their final position
- **AND** no fade-in or slide-up transitions are applied
- **AND** the page does not depend on `IntersectionObserver` triggers to reveal content

#### Scenario: IntersectionObserver fallback
- **GIVEN** the runtime does not support `IntersectionObserver` (or it is mocked to undefined)
- **WHEN** the landing page renders
- **THEN** all sections and grid items are visible immediately at their final position
- **AND** the page renders fully without animation

### Requirement: Section visual differentiation
Each landing page section SHALL use a distinct combination of vertical padding, max-width, and background treatment so the page does not present as a uniform sequence of identical strips.

#### Scenario: Sections have differentiated padding
- **GIVEN** the landing page is rendered
- **WHEN** the user inspects vertical spacing between sections
- **THEN** at least three distinct vertical padding values are used across the sections (e.g., `py-6`, `py-20`, `py-24`)

#### Scenario: Sections have differentiated max-width
- **GIVEN** the landing page is rendered
- **WHEN** the user inspects horizontal content width
- **THEN** the Hero is full-bleed (no max-width constraint on its outer container)
- **AND** the How It Works section uses a narrower max-width than the Featured Products section

#### Scenario: Sections have differentiated background treatments
- **GIVEN** the landing page is rendered
- **WHEN** the user views the page
- **THEN** at least two sections use a distinct background treatment (e.g., glass, gradient, plain) from their neighbors
- **AND** the page does not present all sections with identical background and identical wrapping container

### Requirement: Section file structure
The landing page SHALL be composed from per-section component files located under `frontend/src/pages/landing/sections/`. `LandingPage.tsx` SHALL act as a composer that imports and arranges those section components. Shared landing-page hooks SHALL live under `frontend/src/pages/landing/hooks/`.

#### Scenario: Sections live in dedicated files
- **GIVEN** the repository tree is inspected after the redesign is applied
- **WHEN** the developer looks at `frontend/src/pages/landing/sections/`
- **THEN** there is one file per visible section (Header, Hero, StatsBar, Categories, FeaturedProducts, HowItWorks, Footer)
- **AND** each file exports a default or named React component for that section

#### Scenario: LandingPage is a thin composer
- **GIVEN** `frontend/src/pages/LandingPage.tsx` is inspected
- **WHEN** the developer reads its contents
- **THEN** it imports the section components from `./landing/sections/`
- **AND** it does NOT contain inline section implementations longer than 5 lines each
- **AND** its primary responsibility is composition order and layout wrapper

#### Scenario: Shared hooks live under landing/hooks
- **GIVEN** the redesign includes a shared `useInViewAnimation` hook
- **WHEN** the developer searches for it
- **THEN** it is located at `frontend/src/pages/landing/hooks/useInViewAnimation.ts`
- **AND** it is consumed by section components via relative import
