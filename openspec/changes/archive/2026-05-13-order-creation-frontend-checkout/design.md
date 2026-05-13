## Context

El backend ya expone `POST /api/v1/pedidos` con `CrearPedidoRequest` (items, forma_pago_codigo, direccion_id opcional, notas) y devuelve `PedidoRead` compacto (id, estado_codigo, total, creado_en). El `delivery-addresses-frontend` ya tiene `useAddresses()` para listar direcciones del usuario. El `checkout-validation-frontend` ya valida stock y precios antes de navegar a `/cliente/checkout`. El backend tiene el modelo `FormaPago` con campos `codigo`, `descripcion`, `habilitada` en la tabla `payment_methods`, pero NO hay endpoint para listarlas — el frontend necesita uno para el selector de forma de pago.

El `cartStore` tiene `items: CartItem[]` con `producto_id`, `nombre`, `precio`, `cantidad`, `personalizacion` (string en cart, `number[]` en backend). El `useValidateCart` ya sincronizó precios antes de llegar aquí.

## Goals / Non-Goals

**Goals:**
- Página de checkout completa en `/cliente/checkout` con selección de dirección, forma de pago, resumen con totales y notas.
- Endpoint `GET /api/v1/formas-pago` para listar formas de pago habilitadas.
- Mapeo `CartItem[]` → `CrearPedidoRequest` (incluyendo `personalizacion: string → number[]`).
- Post-creación: redirección a `OrderConfirmationPage` con resumen del pedido.
- Limpieza del carrito tras creación exitosa.

**Non-Goals:**
- Integración con MercadoPago (eso es #27 `payment-mercadopago-frontend`).
- Visualización de pedidos existentes (eso es #28 `order-visualization-frontend`).
- Edición de carrito en checkout (ya se valida antes, el checkout es confirmación).
- Descuentos, cupones, propinas.

## Decisions

### D1 — `CheckoutPage` como orquestador, no como formulario monolítico

La página `CheckoutPage` orquesta tres secciones discretas: `AddressSelector`, `PaymentMethodSelector` y `OrderSummary`. No es un solo `<form>` con TanStack Form porque cada sección maneja su propio estado local. La sumisión del pedido es un `useMutation` independiente que arma el payload a partir de los estados combinados.

**Alternativa**: TanStack Form con `validator` Zod para todo el checkout — sobre-ingeniería porque no hay campos de texto libre típicos de formularios (la dirección se selecciona, la forma de pago se selecciona, las notas son un textarea). Un Zod schema valida el payload ANTES de enviar, pero la UI no necesita un `<form>` single-submit.

**Consecuencia**: Los selectores manejan `selectedAddressId: number | null` y `selectedPaymentMethod: string` como estado local. Al submit, `buildOrderPayload()` arma el `CrearPedidoRequest` y el Zod schema valida.

### D2 — `GET /api/v1/formas-pago` — nuevo endpoint público (autenticado)

El backend no expone las formas de pago. Se agrega un endpoint simple en `features/catalog/router.py`:

```
GET /api/v1/formas-pago → [{ codigo: "MERCADOPAGO", descripcion: "MercadoPago", habilitada: true }, ...]
```

Solo devuelve formas con `habilitada=True`. Requiere autenticación (`Depends(get_current_user)`) pero no rol específico — cualquier usuario autenticado puede listar formas de pago.

**Alternativa**: Hardcodear las formas de pago en el frontend — frágil, si se agrega una nueva forma de pago hay que redeployar el frontend.

**Consecuencia**: Se agrega `FormaPagoRead` schema, `listar_formas_pago()` en service, y endpoint en router. Muy simple (5 líneas de service, 3 de router).

### D3 — Mapeo `CartItem.personalizacion` (string) → `ItemPedidoRequest.personalizacion` (number[])

El `CartItem` del cartStore usa `personalizacion?: string` (label legible, ej. "Sin cebolla"). El backend espera `personalizacion: list[int] | None` (IDs de ingredientes excluidos). El mapeo ocurre en `buildOrderPayload()`:

```ts
personalizacion: item.personalizacionIds ?? null
```

**Decisión**: Se agrega `personalizacionIds?: number[]` a `CartItem` en el cartStore. Cuando el usuario agrega un producto al carrito (en el catálogo o detalle), se guardan los IDs. El campo `personalizacion` (string) se mantiene para display. `personalizacionIds` es el que se envía al backend.

### D4 — Dirección: selector con opción "Retiro en local"

`AddressSelector` consume `useAddresses()` y muestra las direcciones del usuario como radio buttons. La primera opción es "Retiro en local" (sin envío, costo $0). Si no tiene direcciones, solo muestra retiro en local.

El `direccion_id` es `null` cuando se elige retiro en local, que es exactamente lo que espera el backend (RN-PE03 del spec: `direccion_id` opcional).

**Consecuencia**: El envío calculado es `$0` para retiro en local, `$50` (constante v1) para domicilio. Se muestra en el `OrderSummary`.

### D5 — Costo de envío como constante v1

El backend calcula `costo_envio` como `50.00` o `0.00` según si hay `direccion_id`. El frontend lo muestra como estimación pero NO lo calcula — el backend es la fuente de verdad del total. El `OrderSummary` muestra:
- Subtotal: `sum(item.precio × item.cantidad)` (del cartStore)
- Envío: `$50` o `$0` (indicativo, se recalcula en backend)
- Total estimado: subtotal + envío

**Alternativa**: Calcular el total exacto en el frontend y validar contra la respuesta del backend — sobre-ingeniería para v1.

### D6 — `OrderConfirmationPage` como ruta separada

Tras `201 Created`, se navega a `/cliente/pedidos/:id/confirmacion`. Esta página muestra:
- Número de pedido (id)
- Estado: PENDIENTE — Esperando pago
- Resumen de items (desde el cartStore antes de `clearCart()`)
- Total (desde la respuesta `PedidoRead.total`)
- Dirección (si aplica)
- Botones: "Ir a pagar" (#27) y "Ver mis pedidos" (#28)

**Decisión**: Se captura `PedidoRead` del response de la mutation y se pasa como location state. Además se hace `clearCart()` en `onSuccess`. El `OrderConfirmationPage` lee del location state, NO hace un GET del pedido.

**Consecuencia**: Si el usuario hace refresh en `/cliente/pedidos/:id/confirmacion`, no tiene el location state. Se muestra un fallback "Pedido creado" con botón "Ver mis pedidos" + link al detalle del pedido cuando #28 esté implementado.

### D7 — Manejo de errores como toast RFC 7807

El backend devuelve errores en formato RFC 7807 (`ProblemDetails`). El `useCreateOrder` hook mapea:
- `422` con stock insuficiente → toast "Producto sin stock suficiente" + redirigir al carrito
- `422` con forma de pago inválida → toast "Forma de pago no disponible" + re-seleccionar
- `404` dirección no encontrada → toast "Dirección no encontrada. Seleccioná otra."
- `401` → interceptor ya maneja refresh
- `403` → toast "No tenés permisos para crear pedidos."
- Error genérico → toast "Error al crear el pedido. Intentá de nuevo."

Se usa el interceptor de `ApiError` que ya existe en `frontend/src/lib/api/errors.ts`.

### D8 — Estructura de archivos

```
frontend/src/features/checkout/
├── components/
│   ├── CartValidationModal.tsx       ← (ya existe, no se toca)
│   ├── CheckoutPage.tsx             ← orquestador principal
│   ├── AddressSelector.tsx          ← radio group de direcciones + retiro local
│   ├── PaymentMethodSelector.tsx    ← radio group de formas de pago
│   └── OrderSummary.tsx             ← tabla resumen + totales
├── hooks/
│   ├── useValidateCart.ts           ← (ya existe, no se toca)
│   ├── useCreateOrder.ts            ← useMutation POST /pedidos
│   └── usePaymentMethods.ts         ← useQuery GET /formas-pago
├── schemas/
│   └── checkoutSchema.ts            ← Zod schema para CrearPedidoRequest
├── services/
│   ├── orders.service.ts            ← createOrder(payload)
│   └── paymentMethods.service.ts    ← getPaymentMethods()
├── stores/                           ← (vacío, usa cartStore)
└── types/
    ├── validation.types.ts           ← (ya existe, no se toca)
    └── checkout.types.ts             ← CrearPedidoRequest, CheckoutState, etc.

frontend/src/features/orders/
├── components/
│   └── OrderConfirmationPage.tsx    ← pantalla post-creación
├── ... (resto vacío, se pobla en #28)
```

**Backend additions:**

```
backend/features/catalog/
├── router.py                         ← agregar GET /formas-pago
├── schemas.py                         ← agregar FormaPagoRead
└── service.py                         ← agregar listar_formas_pago()

frontend/src/lib/constants/endpoints.ts ← agregar paymentMethods.list
frontend/src/router/AppRoute.tsx        ← reemplazar PlaceholderPage checkout + agregar confirmacion
```

### D9 — Routing en AppRoute.tsx

```tsx
// ANTES (placeholder del change anterior):
<Route path="checkout" element={<PlaceholderPage title="Checkout" ... />} />

// DESPUÉS:
<Route path="checkout" element={<CheckoutPage />} />
<Route path="pedidos/:id/confirmacion" element={<OrderConfirmationPage />} />
```

Ambas rutas dentro del `RoleGuard(['CLIENT'])`.

## Risks / Trade-offs

- **personalizacionIds en CartItem**: Agregar `personalizacionIds` al `CartItem` requiere modificar el cartStore y el punto de addToCart en el catálogo (#21). Si el catálogo actual no guarda IDs de ingredientes excluidos, se necesita agregar esa lógica. → **Mitigación**: Si el catálogo no tiene personalización de ingredientes aún, `personalizacionIds` es `undefined` → se mapea a `null` en el payload. El campo existe en el store para futuro uso, pero no rompe nada si no se pobla.
- **Costo de envío hardcodeado v1**: Mostrar `$50` o `$0` en el frontend es una estimación. Si el backend en v2 cambia la lógica de envío (zona, distancia), el frontend se desincroniza. → **Mitigación**: El `total` confirmado viene del backend — el frontend solo muestra una estimación. Se documenta la constante.
- **OrderConfirmation sin GET**: Si el usuario hace refresh, pierde el resumen. → **Mitigación**: Mostrar fallback con link a "Ver mis pedidos" (#28). En v1 es aceptable.
- **Endpoint GET /formas-pago**: Es el único endpoint nuevo del backend en este change. Es trivial, pero requiere test de integración. → **Mitigación**: Se agrega al test suite junto con el resto del change.