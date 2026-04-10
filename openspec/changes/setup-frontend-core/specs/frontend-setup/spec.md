## ADDED Requirements

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
