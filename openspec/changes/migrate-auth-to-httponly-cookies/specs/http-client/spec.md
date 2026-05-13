# http-client delta

## MODIFIED Requirements

### Requirement: Axios sends cookies and does not inject Bearer tokens
The HTTP client SHALL use `withCredentials: true` and SHALL NOT attach `Authorization: Bearer` from local state.

#### Scenario: Request uses browser cookies
- **WHEN** an API request is made
- **THEN** auth cookies are sent by the browser/client cookie jar
- **AND** no localStorage token is read
