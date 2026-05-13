import axios from 'axios';
import { applyAuthInterceptor } from './interceptors/auth';
import { applyErrorInterceptor } from './interceptors/error';

/**
 * Single axios instance para toda la app.
 *
 * `baseURL` es RELATIVA (`/api/v1`). En dev, el proxy de Vite (vite.config.ts)
 * captura `/api/*` y lo forwardea a `http://localhost:8000`. En prod, el reverse
 * proxy / hosting hace lo mismo — mismo código, sin branching de entorno.
 *
 * Features nunca escriben `/api/v1/...` en el código. Importan desde
 * `lib/constants/endpoints.ts` y pasan paths como `/auth/login`.
 *
 * D7 — Interceptors wired EAGER: se registran acá, antes del `export`,
 * como side effect del módulo. NO se wrappean en main.tsx ni en features.
 * Cualquier import de `apiClient` ya viene con los interceptors activos.
 */
export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// D7 — Eager wiring de interceptors
applyAuthInterceptor(apiClient);
applyErrorInterceptor(apiClient);
