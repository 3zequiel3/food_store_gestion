# Diseño técnico — zustand-stores-base

## Context

El frontend ya tiene scaffolding de Vite + React 19 + TS estricto (`tsconfig.app.json` con `noUnusedLocals`, `verbatimModuleSyntax`) y FSD definido. En `frontend/src/shared/stores/` hay cuatro archivos preexistentes (`authStore.ts`, `cartStore.ts`, `paymentStore.ts`, `uiStore.ts`) que se commitearon con `setup-frontend-core` pero quedaron desalineados respecto a US-000e (ver `proposal.md` para el detalle de gaps). Tampoco hay tests. El package manager es **pnpm**, Zustand está en versión `5.0.12`, vitest `4.x` con `jsdom` ya configurado en `vite.config.ts` y `src/test/setup.ts`.

El próximo change del Sprint 1 (`auth-frontend-interceptor`) consume directamente el contrato del `authStore` desde fuera de React (interceptor Axios), por lo que esta change debe **cerrar el contrato sin huecos** antes de que el interceptor lo importe.

Reglas de negocio aplicables que afectan diseño:
- **RN-AU02 / RN-AU03** — el access token dura 30 min, el refresh 7 días (ambos viven en authStore en runtime, pero solo el access se usa por header).
- **RN-CR01** — el carrito es client-side only.
- **RN-CR02** — el carrito **sobrevive a logout/login**, refresh y cierre de browser.
- **RN-CR03** — agregar un producto repetido suma cantidad, no duplica entrada.
- **RN-CR04 / RN-CR05** — la personalización es array de IDs de ingredientes a excluir.

## Goals / Non-Goals

**Goals:**
- Entregar cuatro stores tipados (cero `any`), idiomáticos en Zustand v5 (`create<TState>()(...)`), con persistencia configurada por store según la spec.
- Exponer un patrón de selectores atómicos consumible por componentes y por código fuera de React (interceptor Axios).
- Cubrir todas las acciones y la persistencia con tests Vitest determinísticos (mock de `localStorage`).
- Cerrar el contrato que `auth-frontend-interceptor` necesita: `useAuthStore.getState().accessToken`, `useAuthStore.getState().updateTokens(...)`, `useAuthStore.getState().logout()`.

**Non-Goals:**
- UI de login, formularios de auth, ProtectedRoute → quedan para `auth-frontend-interceptor` y `navigation-routing-base`.
- Implementar el flujo real de checkout / MercadoPago (vive en `payment-frontend`); aquí solo se modela el shape del store.
- Drawer de carrito y badges en navbar → quedan para `cart-checkout-frontend` y `navigation-routing-base`.
- Integración con TanStack Query → no es responsabilidad de Zustand (separación cliente/servidor, AGENTS.md regla inviolable).
- Devtools de Zustand habilitados en producción (sí en dev, opcional).

## Decisions

### Decisión 1 — Naming idiomático Zustand v5: `useXxxStore`

**Choice:** los stores se exportan como `useAuthStore`, `useCartStore`, `usePaymentStore`, `useUIStore`.

**Rationale:**
- Zustand v5 estableció convención de prefijo `use` porque la función es a la vez un hook React (cuando se usa con selector) y un objeto store (cuando se usa `getState()`).
- El interceptor Axios usa `useAuthStore.getState().accessToken` — funciona idéntico a v4 pero el naming es coherente con el resto del ecosistema React.
- Los stubs actuales exportan `authStore`, `cartStore`, etc. — nombres válidos pero menos idiomáticos. Se renombran.

**Alternativa descartada:** mantener `authStore`. Lo descartamos porque (1) ningún componente real importa todavía esos nombres y (2) genera fricción cuando un developer nuevo lee el código y espera el patrón `use*` estándar.

### Decisión 2 — Selectores atómicos como funciones nombradas exportadas

**Choice:** cada store exporta selectores atómicos como funciones puras junto al hook.

```ts
// authStore.ts
export const useAuthStore = create<AuthState>()(...)
export const selectIsAuthenticated = (s: AuthState) => s.isAuthenticated
export const selectAccessToken = (s: AuthState) => s.accessToken
export const selectHasRol = (rol: RolCode) => (s: AuthState) =>
  s.usuario?.roles.some(r => r.codigo === rol) ?? false
```

Componente:
```tsx
const isAuth = useAuthStore(selectIsAuthenticated)
const isAdmin = useAuthStore(selectHasRol('ADMIN'))
```

**Rationale:**
- US-000e exige "suscripción por slice (no `useStore()` completo)".
- Zustand v5 con selector inline en cada call site funciona, pero genera funciones nuevas en cada render → con `useShallow`/`createWithEqualityFn` se mitiga, pero la solución más limpia y reusable es exportar los selectores como funciones estables.
- Selectores nombrados también sirven como **documentación viva** del API público del store (un grep de `selectAccessToken` te muestra todos los consumers).

**Alternativa descartada:** usar `zustand/react/shallow` con selectores inline. Lo descartamos porque añade ruido en cada call site y los selectores quedan duplicados por componente.

### Decisión 3 — Tipos de dominio fuera de `shared/stores/`

**Choice:**
- `Usuario`, `Rol`, `RolCode`, `AuthTokens` → `frontend/src/entities/user/model/types.ts`. Las entidades de dominio mantienen el naming del backend (`Usuario`, `Rol`); `RolCode` es un union TypeScript con los `codigo` válidos del backend (`ADMIN | STOCK | PEDIDOS | CLIENT`). `AuthTokens` queda en inglés (DTO técnico, no entidad de BD).
- `CartItem`, `Personalizacion` → `frontend/src/entities/order/model/types.ts`. `CartItem` queda en inglés porque la spec canónica lo nombra así (Integrador.txt:256) y el carrito es client-side only (RN-CR01); no existe tabla `Carrito` en backend.
- `Toast` (UI puro), `Theme` → `frontend/src/shared/types/ui.ts` (DTOs técnicos en inglés).

Los stores en `shared/stores/` los importan vía `@/entities/user/model/types` (alias a definir si no existe) o ruta relativa.

**Rationale:**
- FSD: los tipos de dominio pertenecen a `entities/`, no a `shared/`. `shared/` es para código sin dominio.
- Permite que features (`features/auth/`, `features/cart/`) importen los tipos sin tener que pasar por el store.
- Respeta la regla del AGENTS.md: features no importan de features, pero sí pueden importar de entities.

**Alternativa descartada:** dejar todo dentro de `shared/stores/`. Lo descartamos porque mezcla un detalle de implementación (Zustand) con tipos del dominio que tienen vida propia.

### Decisión 4 — Persistencia: qué se persiste y qué no

| Store | Persiste | Clave localStorage | `partialize` excluye |
|---|---|---|---|
| `useAuthStore` | sí | `food-store-auth` | nada transitorio (no hay `isLoading` en este store; si se agrega a futuro, excluir) |
| `useCartStore` | sí | `food-store-cart` | nada — todo el estado del carrito sobrevive |
| `usePaymentStore` | **no** | — | (sin middleware persist) |
| `useUIStore` | parcial | `food-store-ui` | persiste solo `theme`; `sidebarOpen` y `toasts` se regeneran al cargar |

**Rationale:**
- **authStore persiste**: Descripcion.txt §11 lo afirma; el access y refresh token viven en el store y se rehidratan al montar la app. Nota: el doc menciona httpOnly cookie como alternativa a futuro pero el spec actual de US-000e dice localStorage, así que vamos con localStorage. Si en producción se decide endurecer, la migración va en una change futura.
- **cartStore persiste**: RN-CR02 lo exige.
- **paymentStore NO persiste**: US-000e lo pide explícitamente. El estado de checkout es transitorio; rehidratar un `paymentStatus = 'processing'` después de un refresh sería un bug (nunca se completaría).
- **uiStore parcial**: solo `theme` debe sobrevivir; `sidebarOpen` y `toasts` colgados de la sesión anterior molestan al usuario.

### Decisión 5 — `useAuthStore.logout()` NO toca `useCartStore`

**Choice:** `logout()` solo limpia auth state. El carrito queda intacto. La spec del store registra esta decisión de forma explícita.

**Rationale:**
- **RN-CR02**: "El carrito persiste al cerrar el navegador, refresh de página, y logout/login". Si el logout limpiara el carrito violaríamos la regla de negocio.
- Un usuario que se desloguea por sesión vencida y vuelve a entrar debe encontrar su carrito intacto.
- Si en algún flujo específico se necesita limpiar el carrito junto con el logout (raro), el código que orquesta ese flujo llama `useCartStore.getState().clearCart()` explícitamente. Mantener el acoplamiento out-of-band evita sorpresas.

**Alternativa descartada:** que `logout()` llame `clearCart()` "por las dudas". Lo descartamos porque viola RN-CR02.

### Decisión 6 — `clearCart()` se llama desde la lógica de checkout exitoso, no desde el store de pago

**Choice:** cuando el pago se aprueba (paymentStatus = 'approved'), el componente / hook que orquesta el callback de éxito invoca `useCartStore.getState().clearCart()`. El `paymentStore` no conoce al `cartStore`.

**Rationale:**
- Mantiene los stores desacoplados (cada uno único dueño de su slice).
- La orquestación pertenece a un layer superior (feature/page), no al store.

### Decisión 7 — Tests con Vitest, mockeando `localStorage` por suite

**Choice:** cada store tiene su archivo `*.test.ts` en `shared/stores/__tests__/` con:
- Reset del store con `useAuthStore.setState(initialState, true)` en `beforeEach` (replace=true para reset profundo).
- Mock de `localStorage` por suite usando `vi.stubGlobal('localStorage', mockStorage())`.
- Tests por acción (login, logout, addItem, etc.) y por selector (selectHasRol con/sin rol, selectTotalPrice con items vacíos / con items / con personalización).

**Rationale:**
- vitest + jsdom + `@testing-library/jest-dom` ya están instalados (verificado en `package.json` y `vite.config.ts`).
- El test de persistencia es la única parte trickyy: Zustand serializa async; usamos `await waitFor(...)` o forzamos el flush con `useAuthStore.persist.rehydrate()`.

### Decisión 8 — `getState()` para uso fuera de React (interceptor Axios)

**Choice:** documentar en `shared/stores/README.md` que el interceptor de `auth-frontend-interceptor` debe leer/escribir el store así:

```ts
// fuera de React (interceptor Axios)
const token = useAuthStore.getState().accessToken
useAuthStore.getState().updateTokens({ accessToken: '...', refreshToken: '...' })
useAuthStore.getState().logout()
```

**Rationale:**
- US-000e — "Notas Técnicas: usar `useStore.getState()` en el interceptor de Axios (fuera de React)".
- Documentar el patrón ahora ahorra discusión en el siguiente change.

## Diagrama de interacción entre stores

```
                    ┌───────────────────────┐
                    │   feature / page      │
                    │   (orquesta flujos)   │
                    └───────────┬───────────┘
                                │
        ┌──────────────┬────────┼────────┬──────────────┐
        ▼              ▼        ▼        ▼              ▼
  useAuthStore   useCartStore  usePaymentStore   useUIStore   Axios interceptor
  ─────────────  ─────────────  ─────────────────  ───────────  ──(getState)──┐
  accessToken    items[]        checkoutStep      theme                       │
  refreshToken   addItem()      preferenceId      sidebarOpen                 │
  usuario        removeItem()   paymentStatus     toasts                      │
  isAuth         updateQty()    error                                         │
  login()        clearCart()    startCheckout()   setTheme()                  │
  logout() ─────┐                setPreference()  toggleSidebar()             │
  updateTokens()│                updatePayStatus() pushToast()  ◄─────────────┘
                │                resetPayment()
                │
                │ (NO toca cartStore — RN-CR02)
                └─────► (cartStore queda intacto)

  Persistencia:
   useAuthStore  ─► localStorage["food-store-auth"]
   useCartStore  ─► localStorage["food-store-cart"]
   useUIStore    ─► localStorage["food-store-ui"]   (solo theme)
   usePaymentStore  (no persiste)

  Limpieza del carrito al pagar OK:
   payment success callback (en feature/checkout) llama:
     useCartStore.getState().clearCart()
     usePaymentStore.getState().resetPayment()
```

## File layout (FSD)

```
frontend/src/
├── entities/
│   ├── user/
│   │   └── model/
│   │       └── types.ts        # Usuario, Rol, RolCode ('ADMIN'|'STOCK'|'PEDIDOS'|'CLIENT'), AuthTokens
│   └── order/
│       └── model/
│           └── types.ts        # CartItem, Personalizacion
├── shared/
│   ├── stores/
│   │   ├── README.md           # patrón de selectores + getState() fuera de React
│   │   ├── index.ts            # re-exports nombrados
│   │   ├── authStore.ts        # useAuthStore + select*
│   │   ├── cartStore.ts        # useCartStore + select*
│   │   ├── paymentStore.ts     # usePaymentStore + select*
│   │   ├── uiStore.ts          # useUIStore + select*
│   │   └── __tests__/
│   │       ├── authStore.test.ts
│   │       ├── cartStore.test.ts
│   │       ├── paymentStore.test.ts
│   │       └── uiStore.test.ts
│   └── types/
│       └── ui.ts               # Toast, Theme
```

## TypeScript types (referencia para apply)

```ts
// entities/user/model/types.ts
// Naming: Usuario y Rol mantienen el nombre del backend (backend/features/users/models.py::Usuario,
// backend/features/catalog/models.py::Rol). RolCode es el union de los `codigo` válidos del catálogo Rol.
export type RolCode = 'ADMIN' | 'STOCK' | 'PEDIDOS' | 'CLIENT'

export interface Rol {
  id: number
  codigo: RolCode
}

export interface Usuario {
  id: number
  email: string
  nombre: string
  roles: Rol[]
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}

// entities/order/model/types.ts
// Naming: CartItem queda en inglés por mandato de la spec canónica (Integrador.txt:256).
// El carrito es client-side only (RN-CR01), no hay tabla en backend, así que NO hay entidad
// "ItemCarrito" en BD. Los nombres de campo siguen el shape del DTO de Producto del backend
// (snake_case: producto_id, imagen_url) ya que vienen de respuestas server-shape.
export interface Personalizacion {
  ingredientes_excluidos: number[]
}

export interface CartItem {
  producto_id: number
  nombre: string
  precio: number
  cantidad: number
  imagen_url?: string
  personalizacion: Personalizacion
}

// shared/types/ui.ts
export type Theme = 'light' | 'dark'
export interface Toast {
  id: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  durationMs?: number
}
```

**Nota sobre el shape de `CartItem`:** la spec canónica (Integrador.txt:256) lo describe como flat: `producto_id, nombre, precio, cantidad, imagen_url`. La RN-CR05 agrega `personalizacion` con `ingredientes_excluidos`. NO se introducen campos extra (no se anida un objeto `producto: {...}`); cualquier otro dato del producto que la UI necesite se obtiene del catálogo (TanStack Query) con el `producto_id` como clave.

**Nota sobre `Personalizacion`:** el campo `ingredientes_excluidos` usa snake_case porque el backend lo define así en el JSON del pedido (futuro `DetallePedido.personalizacion`); mantener el mismo naming en el cliente evita una capa de transformación.

## Risks / Trade-offs

- **[Riesgo] Tokens en localStorage exponen vulnerabilidad XSS.**
  → **Mitigación:** US-000e lo prescribe explícitamente como localStorage; el tradeoff lo asumió la spec. La defensa real es prevenir XSS (CSP, sanitización, eslint-plugin-react seguros). Si más adelante se decide migrar el refresh token a httpOnly cookie, vivirá en una change futura (`auth-cookie-hardening` por ejemplo) sin pisar este contrato base.

- **[Riesgo] Renombrar `authStore`→`useAuthStore` rompe imports si alguien los usaba.**
  → **Mitigación:** verificado con `rg "from.*shared/stores"` y `rg "authStore\\.|cartStore\\.|paymentStore\\.|uiStore\\."` en `frontend/src/` — los stubs no tienen consumidores reales. La task de implementación incluye un `rg` de verificación previo al rename.

- **[Riesgo] Persistencia de Zustand es asíncrona en algunos navegadores → tests flaky.**
  → **Mitigación:** los tests de persistencia usan `useAuthStore.persist.rehydrate()` y `await` explícito en lugar de timers.

- **[Trade-off] Cuatro stores en vez de uno.**
  → Aceptado: separation of concerns alinea con US-000e y con la rúbrica (`Frontend — Zustand: 10 puntos por 4 stores tipados con persist correcto`). Aceptable: si dos stores empiezan a leerse mutuamente todo el tiempo, se podría considerar slices de un store unificado, pero hoy no hay evidencia de ese acoplamiento.

- **[Trade-off] Selectores como funciones top-level vs hooks compuestos.**
  → Elegimos funciones puras + el hook del store. Más simple, type-safe, sin overhead adicional. El costo es que el consumer escribe `useAuthStore(selectAccessToken)` en vez de `useAuthAccessToken()`. Aceptable.

## Migration Plan

1. Crear `entities/user/model/types.ts` y `entities/order/model/types.ts` con los tipos.
2. Crear `shared/types/ui.ts` con `Toast` y `Theme`.
3. Reescribir uno por uno: `authStore.ts` → `cartStore.ts` → `paymentStore.ts` → `uiStore.ts` (en este orden — auth bloquea a los demás conceptualmente).
4. Actualizar `shared/stores/index.ts` con los exports nuevos (hooks + selectores).
5. Crear `shared/stores/README.md` con el patrón.
6. Escribir los tests Vitest (uno por store).
7. Correr `pnpm tsc -b` (typecheck, no build) y `pnpm test --run` para validar.
8. Smoke manual: `pnpm dev`, abrir devtools → Application → localStorage; agregar un item al cart desde la consola, refrescar la página, verificar que sobrevive.

Sin rollback necesario: el frontend no está desplegado y los stubs viejos no tienen consumers reales.

## Open Questions

1. **¿Habilitamos middleware `devtools` de Zustand en dev?** → Propuesta: sí, condicional por `import.meta.env.DEV`. Si el reviewer prefiere mantener el bundle ultra simple, lo bajamos en `apply`.
2. **¿`Toast` necesita un sistema de auto-dismiss en este change o solo el shape?** → Propuesta: solo el shape y la action `dismissToast`. El componente que renderiza toasts (en `cart-checkout-frontend` o `navigation-routing-base`) implementa el auto-dismiss con `setTimeout` cuando lo necesite. Mantener el store puro.
3. **¿`useAuthStore` debe exponer un `clearAuthAndCart()` helper para flujos donde sí se quiere limpiar todo?** → Propuesta inicial: NO. Si aparece el caso en `auth-frontend-interceptor` o checkout, se agrega entonces como helper externo (no como método del store), respetando RN-CR02 como default.
