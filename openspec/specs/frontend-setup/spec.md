# frontend-setup Specification

## Purpose
TBD - created by archiving change setup-frontend-core. Update Purpose after archive.
## Requirements
### Requirement: Vite + React application initialization
The system SHALL provide a Vite-powered React 18+ application with TypeScript, hot module replacement (HMR), and optimized production builds.

#### Scenario: Application starts in development mode
- **WHEN** the developer runs `pnpm dev`
- **THEN** the application starts on `http://localhost:5173` with HMR enabled

#### Scenario: Application builds for production
- **WHEN** the developer runs `pnpm build`
- **THEN** a production-optimized bundle is generated in `frontend/dist/`

#### Scenario: TypeScript errors are reported
- **WHEN** the developer writes TypeScript code with type errors
- **THEN** the build fails with descriptive error messages

### Requirement: Feature-Sliced Design module structure
The system SHALL organize code into FSD layers: shared → entities → features → widgets → pages → app, with strict dependency direction (lower layers cannot import from higher layers).

#### Scenario: FSD directory structure exists
- **WHEN** the frontend is initialized
- **THEN** `frontend/src/` contains directories: `shared/`, `entities/`, `features/`, `widgets/`, `pages/`, `app/`

#### Scenario: Shared layer contains reusable utilities
- **WHEN** a developer needs a reusable hook, type, or UI component
- **THEN** it is placed in `frontend/src/shared/` and importable by any higher layer

#### Scenario: Feature layer isolates business logic
- **WHEN** a developer creates a new business feature (e.g., auth, cart)
- **THEN** all related components, hooks, and logic live under `frontend/src/features/<feature-name>/`

### Requirement: Environment configuration
The system SHALL read environment variables from `.env` files using Vite's built-in env support (VITE_ prefix).

#### Scenario: API base URL is configurable
- **WHEN** `VITE_API_URL=http://localhost:8000` is set in `.env`
- **THEN** the HTTP client uses that URL as the base for all API requests

#### Scenario: Environment variables are typed
- **WHEN** environment variables are accessed in code
- **THEN** they are typed via `vite-env.d.ts` and accessed through a centralized config module

### Requirement: Package management and dependencies
The system SHALL use pnpm for dependency management with a `package.json` that includes all required dependencies and development scripts.

#### Scenario: Dependencies are installable
- **WHEN** the developer runs `pnpm install`
- **THEN** all required dependencies (react, react-dom, react-router-dom, axios, zustand, tailwindcss) are installed

#### Scenario: Development scripts are available
- **WHEN** the developer checks `package.json` scripts
- **THEN** scripts include: `dev`, `build`, `preview`, `test`, `lint`

## REMOVED Requirements

### Requirement: Feature-Sliced Design module structure

**Reason**: The frontend was restructured to **Feature-First plano** (decision F1 documented in `docs/frontend-architecture.md`). FSD nominal (`shared/entities/features/widgets/pages/app/`) is no longer the project's architecture. The trade-off (loss of rubric points for FSD) was explicitly accepted by the project owner.

**Migration**: Replaced by the `frontend-foundation` capability — see `Requirement: Feature-First plano module structure` in `openspec/specs/frontend-foundation/spec.md`. The new layout uses `api/`, `components/`, `features/`, `lib/`, `pages/`, `router/` with each feature mirroring its backend counterpart by name.

### Requirement: Vite + React application initialization

**Reason**: This requirement is preserved in spirit but the spec text referenced FSD layers in adjacent requirements; this whole capability is being superseded as a single unit so future readers don't have to reconcile FSD vocabulary with the current code.

**Migration**: The Vite + React + TypeScript + HMR baseline is unchanged in the codebase (`pnpm dev` on `:5173`, `pnpm build` to `dist/`). It is no longer specified here because it is treated as a stable infrastructural baseline; if it ever needs spec coverage again, it will be re-added under `frontend-foundation` or a dedicated `frontend-infrastructure` capability.

### Requirement: Environment configuration

**Reason**: The frontend no longer reads `VITE_API_URL` — the Axios `baseURL` is **relative** (`/api/v1`), resolved by Vite proxy in dev and reverse proxy in prod (decision F2). Specifying `VITE_API_URL` is misleading.

**Migration**: The HTTP layer requirement is now `Requirement: Axios client with relative baseURL and interceptor chain` in `frontend-foundation`. The `vite.config.ts` proxy is the only environment-specific knob, and it is documented in `docs/frontend-architecture.md` §3.1.

### Requirement: Package management and dependencies

**Reason**: The dependency list in this requirement is stale (no `lucide-react`, includes `react-hook-form` which is being removed by this change). Keeping it would create drift.

**Migration**: Dependency requirements that matter for product behavior are covered by `frontend-foundation` requirements (`Lucide React iconography with named imports only`, `react-hook-form is removed from dependencies`). The pnpm-only convention is documented in `CLAUDE.md` and `docs/CHANGES.md`.

