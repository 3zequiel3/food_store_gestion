## MODIFIED Requirements

### Requirement: LandingProductCard Component

A simplified product card for public display without cart functionality SHALL be implemented. The card SHALL navigate to the product detail page (`/cliente/catalogo/:id`) regardless of authentication state, since the catalog detail is publicly accessible.

#### Scenario: Card displays product info

- **GIVEN** a `LandingProductCard` receives a `ProductoRead` object
- **WHEN** rendered
- **THEN** it shows: product image (via `ProductImage`), name, price, and description (truncated)
- **AND** it does NOT import or use `useCartStore`
- **AND** it does NOT show "Agregar al carrito" button

#### Scenario: Card navigation always targets product detail

- **GIVEN** the user clicks "Ver más" on a card
- **WHEN** the user is authenticated OR not authenticated
- **THEN** they navigate to `/cliente/catalogo/:id`
- **AND** no branching on `useAuthStore.isAuthenticated()` occurs in `handleVerMas`
