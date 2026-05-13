## REMOVED Requirements

### Requirement: Login form with client-side validation

**Reason**: The previous spec mandated `react-hook-form` (RHF) as the form library. The project standard is now **TanStack Form** with Zod (decision F9 in `docs/frontend-architecture.md`). Re-specifying against TanStack Form prevents future drift back to RHF.

**Migration**: See `Requirement: Login and Register forms with TanStack Form + Zod` in `openspec/specs/frontend-foundation/spec.md`. The 401 → "Credenciales inválidas" inline error and the loading state requirements are preserved; the 429 toast requirement is deferred until a toast layer is wired (see deferred `uiStore` note in `zustand-stores` migration).

### Requirement: Register form with client-side validation

**Reason**: Same as above — RHF is removed; the form contract is re-expressed against TanStack Form.

**Migration**: See `Requirement: Login and Register forms with TanStack Form + Zod` in `frontend-foundation`. Field validation rules (`nombre` min 2 max 80, `apellido` min 2 max 80, `email` valid format, `password` min 8) are preserved in `Requirement: Auth schemas with Zod`. The 409 → inline "email ya registrado" error is preserved.

### Requirement: Login and Register pages wire the forms

**Reason**: Page-level wiring is preserved but described as part of the broader router/layout requirements rather than as a standalone capability item.

**Migration**: Page composition (`LoginPage` renders `LoginForm`, `RegisterPage` renders `RegisterForm`) is implied by the route tree (`Requirement: Route tree with nested guards` in `frontend-foundation`) and the form requirements. The convention "pages contain no form logic, only composition" is documented in `docs/frontend-architecture.md` §9.
