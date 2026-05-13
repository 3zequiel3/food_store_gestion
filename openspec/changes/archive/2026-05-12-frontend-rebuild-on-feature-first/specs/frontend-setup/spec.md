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
