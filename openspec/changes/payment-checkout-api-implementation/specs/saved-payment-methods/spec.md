# Saved Payment Methods — Specification

## Purpose

Store and manage user's saved MercadoPago payment methods (cards) so returning customers can select a previously used card without re-entering card data.

## Requirements

### Requirement: MetodoPagoUsuario persistence

The system SHALL persist saved payment methods in a `metodo_pago_usuario` table with fields: `id`, `user_id` (FK), `mp_customer_id`, `mp_card_id`, `last_four` (4 chars), `expiration_month`, `expiration_year`, `payment_method_id`, `created_at`.

#### Scenario: Save a new card for authenticated user

- **GIVEN** an authenticated user with no saved cards
- **WHEN** `POST /api/v1/metodos-pago` with `{ mp_customer_id, mp_card_id, last_four, expiration_month, expiration_year, payment_method_id }`
- **THEN** responds `201 Created` with the saved `MetodoPagoRead` object
- **AND** the record is persisted in `metodo_pago_usuario`

#### Scenario: Card belongs to requesting user

- **GIVEN** user A has a saved card with id=1
- **WHEN** user B calls `GET /api/v1/metodos-pago`
- **THEN** user B's response does NOT include card id=1

### Requirement: List saved cards

The system SHALL expose `GET /api/v1/metodos-pago` protected by `Depends(get_current_user)` that returns `200 OK` with the authenticated user's saved cards, ordered by `created_at` desc.

#### Scenario: User with saved cards

- **GIVEN** user has 2 saved cards
- **WHEN** `GET /api/v1/metodos-pago`
- **THEN** responds `200 OK` with array of 2 `MetodoPagoRead` objects

#### Scenario: User with no saved cards

- **GIVEN** user has no saved cards
- **WHEN** `GET /api/v1/metodos-pago`
- **THEN** responds `200 OK` with empty array `[]`

### Requirement: Delete saved card

The system SHALL expose `DELETE /api/v1/metodos-pago/{id}` protected by `Depends(get_current_user)` that removes the card if it belongs to the authenticated user.

#### Scenario: Delete own card

- **GIVEN** user owns card with id=5
- **WHEN** `DELETE /api/v1/metodos-pago/5`
- **THEN** responds `204 No Content`
- **AND** subsequent `GET` no longer returns card id=5

#### Scenario: Delete another user's card returns 404

- **GIVEN** card id=5 belongs to user A
- **WHEN** user B calls `DELETE /api/v1/metodos-pago/5`
- **THEN** responds `404 Not Found`

### Requirement: MetodoPagoRead schema

The API response for saved cards SHALL include: `id`, `last_four`, `expiration_month`, `expiration_year`, `payment_method_id`. MUST NOT expose `mp_customer_id` or `mp_card_id` to the frontend.

#### Scenario: Response schema is safe

- **WHEN** a saved card is returned
- **THEN** response contains `id`, `last_four`, `expiration_month`, `expiration_year`, `payment_method_id`
- **AND** response does NOT contain `mp_customer_id` or `mp_card_id`

### Requirement: Frontend saved cards selector

The checkout flow SHALL display the user's saved cards as selectable options with a "Nueva Tarjeta" (New Card) alternative.

#### Scenario: Show saved cards in checkout

- **GIVEN** user has 2 saved cards
- **WHEN** payment page loads
- **THEN** displays 2 card options showing brand, last_four, and expiration
- **AND** displays a "Nueva Tarjeta" option

#### Scenario: Select saved card

- **GIVEN** saved cards are displayed
- **WHEN** user selects a saved card
- **THEN** the checkout proceeds using that card's `mp_card_id` without showing the card form
