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
