## Why

The Food Store frontend needs a robust foundation with industry-standard tooling, modular architecture, and state management. Currently, there is no frontend scaffolding. This change establishes a React + Vite project with Feature-Sliced Design (FSD) architecture, Tailwind CSS styling, and Zustand-based client state management that all downstream features (auth, products, cart, orders) depend on.

## What Changes

- Create frontend project structure following Feature-Sliced Design (FSD) with layers: shared → entities → features → widgets → pages → app
- Install and configure React 18+, Vite, TypeScript, Tailwind CSS, react-router-dom, axios, zustand
- Set up environment configuration (.env, development/production modes)
- Create base layouts, theme configuration, and global styles
- Initialize routing infrastructure with public/private route guards
- Set up Zustand stores foundation with persistence and localStorage integration
- Create HTTP client (axios) with interceptor hooks for future JWT handling
- Initialize vitest and testing configuration

## Capabilities

### New Capabilities
- `frontend-setup`: Vite + React application initialization, FSD module structure, environment configuration, build pipeline
- `theme-styling`: Tailwind CSS configuration, design tokens, global styles, light/dark mode foundation
- `routing-guards`: React Router setup with public/private routes, 404/403 error pages, route guards based on user role
- `zustand-stores`: Four Zustand stores (authStore, cartStore, paymentStore, uiStore) with TypeScript typing and localStorage persistence
- `http-client`: Axios configuration with base URL, request/response interceptors, error handling foundation

### Modified Capabilities
<!-- No existing capabilities are modified in this change -->

## Impact

- **Code**: Creates `/frontend/` directory structure with FSD layers, vite.config.ts, tailwind.config.ts, main.tsx
- **APIs**: Foundation for all future React components and pages
- **Dependencies**: React, Vite, TypeScript, Tailwind CSS, react-router-dom, axios, zustand, vitest
- **Systems**: Establishes the frontend development environment and build pipeline
- **Team**: Defines FSD naming conventions and component organization for all developers
