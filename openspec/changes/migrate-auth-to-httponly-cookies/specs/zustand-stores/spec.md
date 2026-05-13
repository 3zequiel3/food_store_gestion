# zustand-stores delta

## MODIFIED Requirements

### Requirement: Auth store does not persist tokens
The auth store SHALL NOT store or persist `accessToken` or `refreshToken`.

#### Scenario: Auth persistence contains no tokens
- **WHEN** auth state is persisted
- **THEN** only non-sensitive user/session fields are written to localStorage
