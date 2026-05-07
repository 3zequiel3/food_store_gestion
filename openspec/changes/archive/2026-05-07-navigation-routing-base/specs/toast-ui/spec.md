## ADDED Requirements

### Requirement: Toast container renders UIStore toasts
The system SHALL provide a `ToastContainer` component mounted in `AppLayout` that reads `toasts` from `useUIStore` and renders each toast as a visible notification. The container SHALL be positioned fixed at the bottom-right of the viewport and SHALL render above all other content.

#### Scenario: Toast appears when pushToast is called
- **WHEN** `useUIStore.getState().pushToast({ id, message, level: 'error' })` is called from anywhere in the app
- **THEN** the toast message is visible on screen within the same render cycle

#### Scenario: Toast container is always present
- **WHEN** any page in the application renders
- **THEN** the `ToastContainer` is mounted (via `AppLayout`) and ready to display toasts

### Requirement: Toast auto-dismiss
The system SHALL automatically remove a toast after its `durationMs` (default 4000ms if not provided) by calling `useUIStore.getState().dismissToast(id)`.

#### Scenario: Toast disappears after duration
- **WHEN** a toast is pushed with no `durationMs`
- **THEN** the toast is dismissed after 4000ms

#### Scenario: Toast with custom duration
- **WHEN** a toast is pushed with `durationMs: 8000`
- **THEN** the toast is dismissed after 8000ms, not 4000ms

### Requirement: Toast manual dismiss
The system SHALL render a close button (×) on each toast that calls `dismissToast(id)` when clicked.

#### Scenario: User manually dismisses a toast
- **WHEN** the user clicks the × button on a toast
- **THEN** `useUIStore.getState().dismissToast(id)` is called and the toast is removed immediately

### Requirement: Toast visual levels
The system SHALL style each toast according to its `level` field: `error` (red), `success` (green), `warning` (yellow), `info` (blue). The level SHALL also be communicated via a short label prefix or icon.

#### Scenario: Error toast uses red styling
- **WHEN** a toast with `level: 'error'` is rendered
- **THEN** it uses red background or border styling to signal an error

#### Scenario: Success toast uses green styling
- **WHEN** a toast with `level: 'success'` is rendered
- **THEN** it uses green styling
