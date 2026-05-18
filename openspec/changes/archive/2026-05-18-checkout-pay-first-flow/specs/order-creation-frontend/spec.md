## MODIFIED Requirements

### Requirement: Página de checkout con tres secciones

El sistema SHALL renderizar `CheckoutPage` en `/cliente/checkout` con cuatro secciones: `AddressSelector`, `PaymentMethodSelector`, `PaymentForm` (cuando la forma de pago elegida es online) y `OrderSummary`. Cada sección maneja su propio estado local. La página SHALL mostrar un botón "Confirmar y pagar" (online) o "Confirmar pedido" (pickup+efectivo) que dispara la mutación de checkout correspondiente. Mientras la mutation está pendiente, el botón SHALL mostrar un spinner y estar deshabilitado. (US-035)

#### Scenario: Checkout online con tarjeta requiere PaymentForm visible
- **WHEN** un cliente selecciona forma de pago `MERCADOPAGO`
- **THEN** la sección `PaymentForm` (con MP card brick / inputs de tarjeta) se renderiza inline dentro de `CheckoutPage`
- **AND** el botón "Confirmar y pagar" está deshabilitado hasta que `PaymentForm` reporte un `card_token` válido

#### Scenario: Checkout pickup+efectivo no muestra PaymentForm
- **WHEN** el cliente selecciona forma de pago `EFECTIVO` y elige "Retiro en local"
- **THEN** la sección `PaymentForm` NO se renderiza
- **AND** el botón muestra texto "Confirmar pedido"

#### Scenario: Botón deshabilitado durante el checkout
- **WHEN** el cliente hace click en el botón de confirmar y la mutation está en curso
- **THEN** el botón muestra un spinner y está deshabilitado
- **AND** no se puede hacer click de nuevo

---

### Requirement: Selección de dirección con "Retiro en local"

El sistema SHALL mostrar un radio group con las direcciones del usuario (obtenidas via `useAddresses()`) y una opción "Retiro en local (sin envío)" como primera opción. Si el usuario selecciona retiro en local, el `tipo_entrega` SHALL ser `"PICKUP"` y el costo de envío SHALL ser `$0`. Si selecciona una dirección, `tipo_entrega` SHALL ser `"DELIVERY"`, `direccion_id` SHALL ser el ID correspondiente y el costo de envío estimado SHALL ser `$50` (constante v1). Si el usuario no tiene direcciones, solo se muestra retiro en local. (US-035, RN-PE03)

#### Scenario: Selección de retiro en local
- **WHEN** el usuario selecciona "Retiro en local"
- **THEN** el payload tiene `tipo_entrega="PICKUP"` y NO incluye `direccion_id` (o `direccion_id=null` en `POST /checkout/online`)
- **AND** el resumen muestra "Envío: $0"

#### Scenario: Selección de dirección de entrega
- **WHEN** el usuario selecciona una dirección existente
- **THEN** el payload tiene `tipo_entrega="DELIVERY"`, `direccion_id=<id>` y el resumen muestra "Envío: $50"

---

### Requirement: Selección de forma de pago (sin duplicación visual)

El sistema SHALL mostrar un radio group con las formas de pago habilitadas obtenidas via `GET /api/v1/formas-pago`. El usuario SHALL seleccionar exactamente una forma de pago antes de poder confirmar. Cada opción de pago SHALL aparecer **exactamente UNA vez** en el render — el bug visual de opciones duplicadas SHALL ser eliminado. (US-035, D9)

#### Scenario: Listar formas de pago disponibles sin duplicación
- **WHEN** la página de checkout se monta y el endpoint devuelve N formas de pago habilitadas
- **THEN** el componente renderiza exactamente N radio buttons (no 2N ni más)
- **AND** cada radio tiene un `value` único (`codigo`)

#### Scenario: Selección requerida para habilitar confirmar
- **WHEN** el usuario no ha seleccionado una forma de pago
- **THEN** el botón "Confirmar..." está deshabilitado

#### Scenario: Test de regresión del bug de duplicación
- **WHEN** se monta `<PaymentMethodSelector />` con 3 formas de pago
- **THEN** `screen.getAllByRole('radio')` devuelve exactamente 3 elementos
- **AND** los `value` de los radios son únicos

---

### Requirement: Resumen del pedido con totales (informativo)

El sistema SHALL mostrar `OrderSummary` con: tabla de items (nombre, cantidad, precio unitario, subtotal por línea), costo de envío, y total estimado. Los datos vienen del `cartStore`. El total mostrado en el front es **informativo** — el backend recalcula y persiste el total real (D11). El campo de notas opcionales (`notas`, máximo 500 caracteres) se incluye como textarea. (US-035, US-037, US-038, RN-PE08)

#### Scenario: Resumen con dirección de entrega
- **WHEN** se selecciona una dirección
- **THEN** el resumen muestra los items, "Envío: $50", y el total estimado = subtotal + 50

#### Scenario: Resumen con retiro en local
- **WHEN** se selecciona retiro en local
- **THEN** el resumen muestra los items, "Envío: $0", y el total = subtotal

#### Scenario: Notas opcionales
- **WHEN** el usuario escribe notas (hasta 500 caracteres)
- **THEN** el campo `notas` se incluye en el payload; si está vacío, se envía como `null`

---

### Requirement: Hooks de checkout (useCheckoutOnline y useCheckoutPickupEfectivo)

El sistema SHALL exponer dos hooks de TanStack Query en `frontend/src/features/checkout/hooks/`:

- `useCheckoutOnline()`: `useMutation` que envía `POST /api/v1/checkout/online` con `CheckoutOnlineRequest`. Genera un `idempotency_key` (UUID4) al iniciar y lo reutiliza durante la sesión del checkout. Mapea `CartItem[]` a `CheckoutItem[]` con `producto_id`, `cantidad`, `personalizacion`. Incluye `card_token`, `payment_method_id`, `installments`, `identification_type`, `identification_number` desde el `PaymentForm`.
- `useCheckoutPickupEfectivo()`: `useMutation` que envía `POST /api/v1/checkout/pickup-efectivo` con `CheckoutPickupEfectivoRequest`. Solo lleva `items` y `notas`.

El Zod schema `checkoutOnlineSchema` y `checkoutPickupEfectivoSchema` SHALL validar los payloads ANTES de enviar. (US-035, US-036, RN-PE01, RN-PE02, RN-PE07)

#### Scenario: useCheckoutOnline mapea CartItem[] correctamente
- **WHEN** el cliente confirma checkout online con 2 items en el cartStore
- **THEN** el payload `items` tiene 2 entradas con `{producto_id, cantidad, personalizacion}`

#### Scenario: useCheckoutPickupEfectivo no incluye datos de pago
- **WHEN** el cliente confirma pickup+efectivo
- **THEN** el payload NO incluye `card_token`, `payment_method_id`, `installments`, `direccion_id`

#### Scenario: idempotency_key estable durante el checkout
- **GIVEN** el cliente está en `CheckoutPage` y el `idempotency_key` se generó al montar
- **WHEN** la primera mutation falla por error de red y el cliente reintenta
- **THEN** la segunda mutation envía el MISMO `idempotency_key`

#### Scenario: nuevo idempotency_key al regresar al carrito y volver a checkout
- **GIVEN** el cliente abandona `CheckoutPage` y vuelve más tarde
- **WHEN** el `CheckoutPage` se monta nuevamente
- **THEN** se genera un NUEVO `idempotency_key` (UUID4) distinto al anterior

#### Scenario: Validación Zod antes del envío
- **WHEN** el cliente confirma con un payload inválido (e.g. sin `card_token` en online)
- **THEN** la validación Zod falla y se muestra error inline; no se llama a la API

---

### Requirement: Pantalla de confirmación post-creación (OrderConfirmationPage)

Tras `200 OK` de cualquiera de los dos endpoints de checkout, el sistema SHALL redirigir a `/cliente/pedidos/:id/confirmacion` con el response como location state. La página SHALL mostrar: número de pedido (`pedido_id`), estado `"PENDIENTE — Esperando que el local acepte tu pedido"` (semántica nueva, D4), resumen de items (desde cartStore antes de clearCart), total, dirección si aplica, y un botón "Ver mis pedidos". Tras la redirección exitosa, el carrito SHALL ser limpiado via `cartStore.clearCart()`. Ya NO se incluye el botón "Ir a pagar" porque el pago ya ocurrió (online) o ocurrirá en mostrador (pickup+efectivo). (US-071)

#### Scenario: Confirmación post-checkout online aprobado
- **WHEN** `POST /checkout/online` devuelve `200` con `mp_status="approved"`
- **THEN** se navega a `/cliente/pedidos/<pedido_id>/confirmacion` mostrando ID, items, total, dirección (si aplica), estado "PENDIENTE — Esperando que el local acepte tu pedido"
- **AND** el carrito queda vacío
- **AND** NO se muestra ningún botón "Ir a pagar"

#### Scenario: Confirmación post-checkout pickup+efectivo
- **WHEN** `POST /checkout/pickup-efectivo` devuelve `200`
- **THEN** se navega a la confirmación mostrando "Retiro en local — Pagás al retirar"
- **AND** el carrito queda vacío

#### Scenario: Fallback sin location state (refresh)
- **WHEN** el usuario llega a la confirmación sin location state
- **THEN** se muestra un fallback genérico "Pedido creado" con botón "Ver mis pedidos"

---

### Requirement: Manejo de errores del backend

El sistema SHALL mapear errores del backend a toasts informativos:
- `402` con `code="payment_rejected"` → toast con `detail` (mensaje user-friendly mapeado por `friendlyMessageFor(status_detail)`). El usuario permanece en `CheckoutPage` y puede reintentar.
- `402` con `code="payment_pending_not_accepted"` → toast "Tu pago quedó en revisión y no podemos confirmar el pedido. Probá con otra tarjeta o elegí pago en efectivo al retirar." El usuario permanece en `CheckoutPage`.
- `502` con `code="mp_unreachable"` → toast "MercadoPago no respondió. Intentá de nuevo en un momento." El usuario permanece en `CheckoutPage` con el mismo `idempotency_key` (puede reintentar).
- `422` con stock insuficiente → toast "Producto sin stock suficiente. Volvé al carrito para ajustar." + botón para volver al catálogo.
- `404` dirección no encontrada → toast "Dirección no encontrada. Seleccioná otra." + limpiar selección.
- `401`/`403` → manejo por interceptor existente.
- Error genérico → toast "Error al procesar el checkout. Intentá de nuevo."

#### Scenario: Rejected payment muestra toast con mensaje user-friendly
- **WHEN** el backend responde `402` con `mp_status="rejected"`, `status_detail="cc_rejected_insufficient_amount"`
- **THEN** se muestra toast con "Saldo insuficiente. Probá con otra tarjeta."
- **AND** el usuario permanece en `CheckoutPage`
- **AND** el `cartStore` no se limpia

#### Scenario: Pending payment muestra toast claro (modo estricto)
- **WHEN** el backend responde `402` con `code="payment_pending_not_accepted"`
- **THEN** se muestra toast con el mensaje del modo estricto
- **AND** el usuario permanece en `CheckoutPage`

#### Scenario: MP unreachable permite reintentar con mismo idempotency_key
- **WHEN** el backend responde `502` con `code="mp_unreachable"`
- **THEN** el toast invita a reintentar
- **AND** si el usuario clickea "Confirmar y pagar" otra vez, se reutiliza el mismo `idempotency_key`

---

### Requirement: Agregar `personalizacionIds` a CartItem en cartStore (sin cambios)

El sistema SHALL mantener el campo opcional `personalizacionIds?: number[]` en el tipo `CartItem` del cartStore (sin cambios respecto al spec original). El mapeo a `personalizacion: list[int] | null` en el payload de checkout se preserva.

#### Scenario: Item con personalizacionIds en el carrito
- **WHEN** se agrega un producto con `personalizacionIds: [3, 7]`
- **THEN** el `CheckoutItem` tiene `personalizacion: [3, 7]`

#### Scenario: Item sin personalizacionIds
- **WHEN** se agrega un producto sin `personalizacionIds`
- **THEN** el `CheckoutItem` tiene `personalizacion: null`
