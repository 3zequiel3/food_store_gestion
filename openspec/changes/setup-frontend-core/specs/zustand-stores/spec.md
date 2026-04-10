## ADDED Requirements

### Requirement: Auth store with JWT management
The system SHALL provide an authStore (Zustand) that manages authentication state: user data, access token, refresh token, and login/logout actions.

#### Scenario: authStore tracks authentication state
- **WHEN** the application initializes
- **THEN** authStore loads persisted auth data from localStorage (token, user profile)

#### Scenario: Login action updates authStore
- **WHEN** a user successfully logs in
- **THEN** authStore stores the access token, refresh token, and user profile (id, email, role)

#### Scenario: Logout action clears authStore
- **WHEN** a user logs out
- **THEN** authStore clears all auth data and removes persisted state from localStorage

### Requirement: Cart store with item management
The system SHALL provide a cartStore (Zustand) that manages shopping cart state: items, quantities, totals, and CRUD operations.

#### Scenario: cartStore persists items to localStorage
- **WHEN** a user adds a product to the cart
- **THEN** cartStore saves the cart items to localStorage so they survive page refresh

#### Scenario: cartStore calculates totals
- **WHEN** the cart contains items with quantities and prices
- **THEN** cartStore computes subtotal, item count, and total automatically

#### Scenario: cartStore clears on checkout
- **WHEN** an order is successfully placed
- **THEN** cartStore clears all items and resets totals

### Requirement: Payment store with payment state
The system SHALL provide a paymentStore (Zustand) that manages payment flow state: selected method, payment status, external payment ID.

#### Scenario: paymentStore tracks payment method
- **WHEN** a user selects a payment method (EFECTIVO, TARJETA, MERCADOPAGO)
- **THEN** paymentStore stores the selected method

#### Scenario: paymentStore tracks payment status
- **WHEN** a payment is initiated or completed
- **THEN** paymentStore updates status (pending, processing, completed, failed)

### Requirement: UI store with application state
The system SHALL provide a uiStore (Zustand) that manages UI state: sidebar visibility, dark mode, loading states, toast notifications.

#### Scenario: uiStore manages sidebar
- **WHEN** the user toggles the sidebar
- **THEN** uiStore updates sidebar visibility and the UI re-renders accordingly

#### Scenario: uiStore manages dark mode preference
- **WHEN** the user toggles dark mode
- **THEN** uiStore saves the preference and persists it to localStorage

#### Scenario: uiStore manages loading state
- **WHEN** an API request is in progress
- **THEN** uiStore sets a global loading flag that components can subscribe to

### Requirement: Store persistence with localStorage
The system SHALL persist selected store slices to localStorage using Zustand's persist middleware.

#### Scenario: Stores survive page refresh
- **WHEN** the user refreshes the page
- **THEN** authStore, cartStore, and uiStore restore state from localStorage

#### Scenario: Sensitive data is handled carefully
- **WHEN** authStore persists to localStorage
- **THEN** only the access token and user profile are stored (NOT the refresh token in localStorage; refresh token uses httpOnly cookie)
