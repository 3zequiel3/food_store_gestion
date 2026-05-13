## ADDED Requirements

### Requirement: Button component
The system SHALL provide a reusable Button component with the following variants: `primary`, `secondary`, `ghost`, `destructive`, `outline`. Each variant SHALL have distinct visual styling using design tokens. The Button SHALL support sizes `sm`, `md`, `lg`. The Button SHALL show a loading spinner when `isPending` prop is true and SHALL disable interaction during loading.

#### Scenario: Primary button renders with correct tokens
- **WHEN** rendering `<Button variant="primary">Click</Button>`
- **THEN** the button has `bg-primary text-primary-foreground` styling

#### Scenario: Button shows loading state
- **WHEN** rendering `<Button isLoading>Save</Button>`
- **THEN** the button shows a spinner and is disabled

### Requirement: Input component
The system SHALL provide a reusable Input component that wraps native `<input>` with label, error message display, and optional icon slots. The input SHALL use `--color-input`, `--color-ring`, and `--color-destructive` tokens.

#### Scenario: Input renders with label and error
- **WHEN** rendering `<Input label="Email" error="Required" />`
- **THEN** the label text is visible and the error message is rendered in `text-destructive`

### Requirement: Card component
The system SHALL provide a Card component with variants: `elevated` (glass surface with shadow), `outlined` (border only), `interactive` (hover lift effect). Cards SHALL use `--color-glass` or `--color-card` tokens.

#### Scenario: Elevated card has glass effect
- **WHEN** rendering `<Card variant="elevated">Content</Card>`
- **THEN** the card has `backdrop-blur-xl`, glass background, and shadow

### Requirement: Badge component
The system SHALL provide a Badge component that uses semantic tokens (`--color-success`, `--color-warning`, `--color-destructive`, etc.) for status display. The Badge SHALL replace all hardcoded color values in OrderStatusBadge.

#### Scenario: Success badge uses success tokens
- **WHEN** rendering `<Badge variant="success">Entregado</Badge>`
- **THEN** the badge has `bg-success/15 text-success ring-success/30` styling
