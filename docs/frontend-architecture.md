# Frontend Architecture — Food Store

Documenta la estructura del frontend y los puntos de acople con el backend FastAPI. Este archivo es **complementario** a `Descripcion.txt` (que describe el FSD canónico). Acá vive la implementación real, las desviaciones intencionales y las decisiones tomadas.

---

## 1. Stack

| Capa | Tool | Versión |
|------|------|---------|
| Bundler | Vite | 8.x |
| Framework | React | 19.x |
| Lenguaje | TypeScript | 6.x |
| Server state | TanStack Query | 5.x |
| Client state | Zustand | 5.x |
| Forms | TanStack Form | 1.x |
| HTTP | Axios | 1.x |
| Routing | react-router-dom | 7.x |
| Tablas | TanStack Table | 8.x |
| Validación | Zod | 4.x |
| Estilos | Tailwind CSS | 4.x |
| Iconos | lucide-react | 0.511.x |
| Package manager | **pnpm** (no npm) | — |

> **Notas**: `react-hook-form` y `@hookform/resolvers` fueron eliminados en `frontend-rebuild-on-feature-first` (2026-05-12). TanStack Form es el ÚNICO sistema de formularios del proyecto.

---

## 2. Estructura de carpetas

```
frontend/src/
├── api/
│   ├── client.ts              # Instancia única de axios (baseURL relativa /api/v1)
│   └── interceptors/          # (pendiente) auth header, refresh rotation, RFC 7807
│
├── assets/                    # PNG, SVG, fonts
│
├── components/
│   ├── common/                # botones, inputs, modales genéricos (sin lógica de negocio)
│   ├── layout/                # navbar, sidebar, footer, page shells
│   └── ui/                    # primitives (Button, Input, Card) — base del design system
│
├── features/                  # ★ Feature-First — espejo del backend
│   ├── addresses/             # ↔ backend/features/addresses
│   ├── auth/                  # ↔ backend/features/auth
│   ├── cart/                  # solo frontend (sin contraparte backend)
│   ├── catalog/               # ↔ backend/features/{products, categories, ingredients}
│   ├── checkout/              # solo frontend (orquesta cart → orders → payments)
│   ├── orders/                # ↔ backend/features/orders
│   ├── payments/              # ↔ backend/features/payments
│   └── profile/               # ↔ backend/features/users
│
│   Cada feature tiene la misma estructura interna:
│   features/<f>/
│   ├── components/            # UI específica de la feature
│   ├── hooks/                 # useXxx — combina queries + estado local
│   ├── schemas/               # Zod schemas para validar requests/responses
│   ├── services/              # llamadas a apiClient usando ENDPOINTS
│   ├── stores/                # Zustand stores (si la feature tiene client state)
│   └── types/                 # tipos TypeScript de la feature
│
├── lib/
│   ├── constants/
│   │   └── endpoints.ts       # ★ todos los paths del backend, tipados
│   ├── helpers/               # funciones puras (format, parse, calc)
│   └── utils/                 # utilidades cross-cutting
│
├── pages/
│   ├── admin/                 # layouts y páginas del dashboard admin
│   └── client/                # layouts y páginas del cliente
│
├── router/
│   └── AppRoute.tsx           # configuración de rutas
│
├── App.tsx                    # BrowserRouter wrapper
├── main.tsx                   # createRoot + QueryClientProvider
└── index.css                  # Tailwind imports
```

### Decisión: Feature-First plano, NO FSD nominal

`Descripcion.txt:99` describe FSD (Feature-Sliced Design) con 6 capas: `app → pages → widgets → features → entities → shared`.

**El frontend actual NO usa FSD nominal**. Usa **Feature-First plano**, donde:
- `app/` está distribuido entre `App.tsx`, `main.tsx`, `router/`
- `shared/` está distribuido entre `api/`, `components/`, `lib/`, `assets/`
- `entities/` no existe — los tipos viven dentro de cada `features/<f>/types/`
- `widgets/` no existe — la composición cross-feature ocurre en `pages/`

**Por qué**:
1. **Espejo del backend**: `features/auth` ↔ `backend/features/auth`, `features/orders` ↔ `backend/features/orders`. Nombrando idéntico se reduce la fricción cognitiva.
2. **Más plano = menos imports indirectos**: con FSD nominal, importar un tipo de `entities/` desde una `feature/` agrega un nivel de indirección que rara vez paga.
3. **Estructura ya en producción**: el frontend arrancó así y reorganizar para conformar FSD nominal es trabajo cosmético sin ganancia funcional.

**Tradeoff que aceptamos**: se pierden puntos de rúbrica (la evaluación menciona FSD explícitamente en `Descripcion.txt:591`). Lo asumimos.

**Riesgo a vigilar**: tipos de dominio (`Producto`, `Pedido`, `Usuario`) duplicados en múltiples `features/<f>/types/`. Si aparece duplicación real, agregar `src/types/` (o `src/entities/`) y mover ahí. Por ahora, mientras los tipos vivan en una sola feature, queda en su feature.

---

## 3. Contrato con el backend (los 3 puntos de acople)

El frontend está acoplado al backend en **exactamente 3 lugares**. El resto es libre.

### 3.1 — `vite.config.ts` — Proxy de desarrollo

```ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

- **Sin `rewrite`** — forwarda el path tal cual. El backend recibe `/api/v1/...` idéntico a lo que pidió el front.
- **Puerto 5173 fijo** — está en `CORS_ORIGINS` del backend (`.env`).
- **Solo dev**: en prod, el reverse proxy / Vercel / Nginx debe enrutar `/api/*` al backend.

**Bug corregido en este setup**: el rewrite original (`path.replace(/^\/api/, '')`) tiraba `/api` del path, rompiendo el routing. Sacado.

### 3.2 — `api/client.ts` — Axios instance

```ts
export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});
```

- **`baseURL` relativo** (`/api/v1`, no `http://localhost:8000/api/v1`). En dev pasa por el proxy de Vite; en prod por el reverse proxy. **Mismo código, sin branching por ambiente.**
- **Sin interceptors todavía** — el archivo `interceptors/` queda pendiente para:
  - inyectar `Authorization: Bearer ${access_token}` desde `authStore`
  - manejar 401 con refresh rotation + cola de requests pendientes
  - parsear errores RFC 7807 + `errors[]` en un `ApiError` tipado

### 3.3 — `lib/constants/endpoints.ts` — Single source of truth de paths

Todos los endpoints del backend, agrupados por feature, con types. Las features importan de acá, **nunca hardcodean paths**.

```ts
import { apiClient } from '@/api/client';
import { ENDPOINTS } from '@/lib/constants/endpoints';

apiClient.post(ENDPOINTS.auth.login, { email, password });
apiClient.get(ENDPOINTS.pedidos.detail(123));
```

Estructura:
- Static paths: `'/auth/login'`
- Dynamic paths: funciones `(id: number) => string`
- Agrupado por feature backend, no por feature frontend (porque un feature frontend puede llamar a varios endpoints backend — ej. `catalog` usa `productos`, `categorias`, `ingredientes`)

---

## 4. Mapeo feature frontend ↔ backend

| Feature frontend | Endpoints backend usados |
|------------------|--------------------------|
| `auth` | `ENDPOINTS.auth.*` |
| `profile` | `ENDPOINTS.usuarios.*` |
| `catalog` | `ENDPOINTS.productos.*` + `ENDPOINTS.categorias.*` + `ENDPOINTS.ingredientes.*` |
| `cart` | (frontend-only, persistido en localStorage vía Zustand) |
| `checkout` | `ENDPOINTS.pedidos.create` + `ENDPOINTS.pagos.create` |
| `orders` | `ENDPOINTS.pedidos.*` |
| `payments` | `ENDPOINTS.pagos.*` |
| `addresses` | `ENDPOINTS.direcciones.*` |
| (admin pages) | `ENDPOINTS.adminUsuarios.*` + `ENDPOINTS.adminMetricas.*` |

---

## 5. Flujo de una request — diagrama

```
┌─────────────────────────────────────────────────────────────────┐
│  Feature code:                                                  │
│    apiClient.post(ENDPOINTS.auth.login, { email, password })    │
│                                                                 │
│            │                                                    │
│            ▼  (axios resuelve baseURL + path)                   │
│                                                                 │
│    POST /api/v1/auth/login                                      │
│                                                                 │
│            │                                                    │
│            ▼  (dev server :5173 intercepta /api/*)              │
│                                                                 │
│    Vite proxy → http://localhost:8000/api/v1/auth/login         │
│                                                                 │
│            │                                                    │
│            ▼  (CORS automático con changeOrigin)                │
│                                                                 │
│    FastAPI router auth → service → uow → repository → DB        │
│                                                                 │
│            │                                                    │
│            ▼                                                    │
│                                                                 │
│    Response { access_token, refresh_token, token_type, ... }    │
│                                                                 │
│            │                                                    │
│            ▼  (Vite proxy devuelve al :5173)                    │
│                                                                 │
│    axios resuelve → response.data                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Decisiones tomadas

| ID | Decisión | Razón |
|----|----------|-------|
| **F1** | Feature-First plano, NO FSD nominal | Espejo del backend, menor indirección |
| **F2** | `baseURL: '/api/v1'` relativo en axios | Un solo código para dev y prod, proxy resuelve |
| **F3** | Vite proxy `/api → :8000` sin rewrite | Forward as-is, el backend espera `/api/v1/...` |
| **F4** | `lib/constants/endpoints.ts` como SoT de paths | Renombre de ruta = 1 lugar, no N services |
| **F5** | `ENDPOINTS` agrupado por backend feature | Múltiples features frontend usan los mismos backend endpoints |
| **F6** | Dynamic paths como funciones `(id) => string` | Type-safe sin template strings dispersos |
| **F7** | Trailing slash idéntico al backend (`/productos/` con, `/auth/login` sin) | Evita el 307 redirect que vimos en TestSprite |
| **F8** | Interceptors NO en `client.ts` — viven en `api/interceptors/` | Separación: client = transporte; interceptors = lógica de auth/error |
| **F9** | TanStack Form sobre react-hook-form | Alineado con TanStack Query/Table — ecosystem coherente |
| **F10** | Tipos cross-feature en `features/<f>/types/` hasta que duplique | Empezar plano, refactorizar a `src/entities/` solo cuando duela |
| **F11** | Errores en español (parse de RFC 7807 + `errors[]`) — handler a definir en interceptors | El backend devuelve mensajes en español; el front los muestra tal cual |
| **F12** | CORS port 5173 fijo en `vite.config.ts` | `CORS_ORIGINS` del backend ya lo permite, romperlo es un dolor |

---

## 7. Riesgos abiertos

| # | Riesgo | Mitigación pendiente |
|---|--------|----------------------|
| R1 | Schema drift entre Zod schemas del front y Pydantic del backend | Codegen con `openapi-typescript` desde `/openapi.json` |
| R2 | Refresh dance mal implementado (race conditions, doble refresh) | Implementar interceptor con cola single-flight |
| R3 | Decimal serializado como string en JSON → si parseás con `Number()` perdés precisión en cart/checkout | Usar `decimal.js` o `Big.js` en cart/checkout |
| R4 | Sin tipos del backend en el front (todos los responses son `any` o tipados a mano) | Codegen → genera `src/api/generated.ts` |
| R5 | `cart` y `checkout` son frontend-only — si el backend cambia el contrato de `/pedidos`, hay que actualizar `checkout` a mano | Documentar el contrato en `checkout/types/` y revisar en cada change OPSX de orders |
| R6 | TanStack Query no configurado con defaults (staleTime, retry, etc.) | Definir defaults globales en `main.tsx` cuando arranque la primera query |

---

## 8. Cómo agregar un endpoint nuevo

Si Neyén o vos agregan una ruta nueva en el backend, el flujo del front es:

1. **Verificar** que el path no exista en `lib/constants/endpoints.ts`.
2. **Agregarlo** en el grupo correcto (o crear grupo nuevo si es un módulo nuevo).
3. **Crear el service** en `features/<f>/services/` que usa el endpoint con `apiClient`.
4. **Crear el hook** en `features/<f>/hooks/` que envuelve la query (`useQuery` o `useMutation`).
5. **Crear el schema Zod** en `features/<f>/schemas/` que matchea el shape del response del backend.
6. **Tipar el response** (idealmente desde codegen, mientras tanto a mano).

---

## 9. Cómo agregar una feature nueva

1. Crear `features/<nombre>/{components, hooks, schemas, services, stores, types}/`.
2. Si tiene contraparte backend, mantener el mismo nombre.
3. Si NO tiene contraparte backend (frontend-only, ej. `cart`), documentarlo en este archivo.
4. Si tiene client state persistente, crear `stores/<nombre>Store.ts` con Zustand `persist` middleware sobre localStorage.
5. NO duplicar tipos que ya viven en otra feature — importar o promover a `src/types/`.

---

## 10. Antipatrones — qué NO hacer

- ❌ Hardcodear paths: `axios.get('/api/v1/pedidos')` — usar `ENDPOINTS.pedidos.list`.
- ❌ Usar `http://localhost:8000` en código de feature — solo en `vite.config.ts`.
- ❌ Importar de `react-hook-form` — usar TanStack Form.
- ❌ Manejar tokens fuera del `authStore` de Zustand.
- ❌ Hacer fetch directo con `fetch()` — usar siempre `apiClient`.
- ❌ Mezclar client state (Zustand) con server state (TanStack Query). Si el dato viene del backend, va en Query. Si vive solo en el cliente (cart, theme, sidebar abierto), va en Zustand.
- ❌ Crear un store global "para todo" — un store por concern (auth, cart, ui, payment).
- ❌ **Namespace import de lucide-react**: `import * as Icons from 'lucide-react'` — carga los ~1500 íconos en el bundle. Usá siempre named imports: `import { Home, ShoppingCart } from 'lucide-react'`. ESLint ya bloquea el namespace import (regla `no-restricted-imports` en `eslint.config.js`).

---

## 12. Design tokens — Tailwind v4 dark-first

### Stack

- **Tailwind CSS v4** con plugin `@tailwindcss/vite` (bundler-native, sin PostCSS manual).
- **Directiva `@theme`** en `frontend/src/index.css` — los tokens viven en CSS, no en `tailwind.config.ts`.
- **Modo dark-first**: los valores del `@theme` son los tokens DARK. El tema claro se activa con `html.light { ... }`.

### Ubicación

```
frontend/src/index.css  ←  source of truth de todos los tokens
```

`tailwind.config.ts` queda vacío (`export default {}`). Tailwind v4 hace auto-content-scanning — no necesita la lista de `content:[]`.

### Tokens disponibles

| Categoría | Variables |
|-----------|-----------|
| **Superficies** | `--color-background`, `--color-foreground` |
| **Elevadas** | `--color-card`, `--color-card-foreground`, `--color-popover`, `--color-popover-foreground` |
| **Brand** | `--color-primary`, `--color-primary-foreground` |
| **Neutras** | `--color-secondary`, `--color-muted`, `--color-accent` (+ foregrounds) |
| **Semánticas** | `--color-destructive`, `--color-success`, `--color-warning` (+ foregrounds) |
| **Utility** | `--color-border`, `--color-input`, `--color-ring` |
| **Tipografía** | `--font-sans`, `--font-mono` |
| **Radios** | `--radius-sm`, `--radius`, `--radius-lg`, `--radius-xl`, `--radius-2xl` |
| **Sombras** | `--shadow-sm`, `--shadow`, `--shadow-md`, `--shadow-lg`, `--shadow-xl` |

### Formato: OKLCH

Los colores usan **OKLCH** (Oklch Color Space), no hex ni RGB.

```css
--color-primary: oklch(0.72 0.18 50);  /* warm orange — food-oriented */
```

OKLCH es perceptualmente uniforme: dos colores con igual `L` (lightness) se ven igualmente brillantes. Permite mezclas predecibles y accesibles. Tailwind v4 lo usa internamente.

### Cómo usar tokens en componentes

Usá las utility classes que Tailwind genera automáticamente a partir de los tokens:

```tsx
// ✅ Correcto — via utility classes derivadas del token
<button className="bg-primary text-primary-foreground">...</button>
<div className="bg-card border border-border">...</div>

// ❌ Incorrecto — hex hardcodeado (ESLint no lo catchea pero es antipatrón)
<button style={{ backgroundColor: '#f97316' }}>...</button>
```

### Cómo extender tokens

Agregá el token en `src/index.css` dentro de `@theme { }`:

```css
@theme {
  /* ... tokens existentes ... */
  --color-brand-accent: oklch(0.65 0.20 180);  /* nuevo token */
}
```

Tailwind lo expone automáticamente como `bg-brand-accent`, `text-brand-accent`, etc.

### Dark/light switching

El switching es CSS-only, sin React re-render:

```js
// Activar light mode
document.documentElement.classList.add('light');

// Volver a dark
document.documentElement.classList.remove('light');
```

El toggle UI y la persistencia de preferencia (localStorage) se implementan cuando se cree `uiStore`.

### Antipatrón: hex hardcodeado

```tsx
// ❌ Nunca hacer esto en componentes
<div className="bg-[#1a1a1a] text-[#ff6b00]">

// ✅ En su lugar
<div className="bg-background text-primary">
```

El script de validación `rg '#[0-9a-fA-F]{3,8}' src/components/ src/features/` debería retornar 0 matches.

---

## 11. Pendientes inmediatos

- ~~[ ] Implementar interceptor de auth en `api/interceptors/auth.ts`~~ ✅ Resuelto en `frontend-rebuild-on-feature-first`
- ~~[ ] Implementar interceptor de error → `ApiError` tipado en `api/interceptors/error.ts`~~ ✅ Resuelto en `frontend-rebuild-on-feature-first`
- ~~[ ] Crear `authStore` de Zustand con `persist` middleware~~ ✅ Resuelto en `frontend-rebuild-on-feature-first`
- ~~[ ] Definir defaults globales de TanStack Query en `main.tsx`~~ ✅ Resuelto en `frontend-rebuild-on-feature-first`
- ~~[ ] Limpiar `react-hook-form` y `@hookform/resolvers` del `package.json`~~ ✅ Resuelto en `frontend-rebuild-on-feature-first`
- [ ] Configurar codegen: `pnpm gen:api` que corre `openapi-typescript` — aún pendiente (R4, out of scope hasta Fase B estable)
- [ ] Implementar user menu completo en `TopNavbar` (dropdown, no solo logout)
- [ ] Agregar toast global (sonner/react-hot-toast) cuando haya `uiStore` o necesidad real
- [ ] Tests unitarios para `authStore` y `cartStore` con Vitest (coverage de reducers)
