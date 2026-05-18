## REMOVED Requirements

### Requirement: Crear pedido desde el carrito (atomicidad)

**Reason**: el endpoint `POST /api/v1/pedidos/` se elimina. La creación de pedidos vive ahora en la capability `checkout` (`POST /api/v1/checkout/online` y `POST /api/v1/checkout/pickup-efectivo`), que envuelve la creación de Pedido y el cobro (cuando aplica) en una sola operación atómica. Crear un Pedido antes de pagar dejaba pedidos huérfanos en `PENDIENTE` cuando el cliente cerraba el navegador.

**Migration**: el frontend migra a `POST /api/v1/checkout/online` (cuando hay forma de pago online) o `POST /api/v1/checkout/pickup-efectivo` (cuando es pickup+efectivo). Ver capability `checkout` (`openspec/changes/checkout-pay-first-flow/specs/checkout/spec.md`).

---

### Requirement: Snapshots inmutables de precio y dirección

**Reason**: la responsabilidad de capturar snapshots inmutables migra a la capability `checkout`. La lógica es la misma — solo cambia el endpoint que la invoca.

**Migration**: el requirement "Snapshots inmutables al crear el pedido" en `checkout/spec.md` cubre este comportamiento.

---

### Requirement: Validación de stock con lock pesimista dentro de la transacción

**Reason**: la validación de stock con `SELECT FOR UPDATE` migra a la capability `checkout` (`POST /api/v1/checkout/*`).

**Migration**: el requirement "Validación server-side de carrito" en `checkout/spec.md` cubre este comportamiento.

---

### Requirement: Validación de forma de pago contra el catálogo

**Reason**: la validación de `forma_pago_codigo` migra a la capability `checkout`. En `POST /checkout/online`, la forma de pago es siempre `MERCADOPAGO` (implícito por el endpoint). En `POST /checkout/pickup-efectivo`, es siempre `EFECTIVO`. Los códigos siguen viviendo en `payment_methods` para listados de UI.

**Migration**: el listado de formas de pago `GET /api/v1/formas-pago` se mantiene sin cambios. La validación contra catálogo ahora vive en `CheckoutService`, no en `OrderService`.

---

### Requirement: Validación de propiedad de la dirección (anti-leak D6)

**Reason**: migra a la capability `checkout` (`POST /checkout/online` con `tipo_entrega=DELIVERY`). El comportamiento "404, no 403" se preserva en el nuevo endpoint.

**Migration**: el requirement "Validación server-side de carrito" en `checkout/spec.md` incluye este comportamiento.

---

### Requirement: Retiro en local (direccion_id opcional)

**Reason**: el "retiro en local" pasa a estar explícitamente en `POST /api/v1/checkout/pickup-efectivo`, donde `direccion_id` no se acepta (es siempre pickup). Para online + pickup, se usa `POST /checkout/online` con `tipo_entrega=PICKUP` y `direccion_id=null`.

**Migration**: el nuevo endpoint `POST /checkout/pickup-efectivo` cubre el caso retiro+efectivo. Para retiro+online, se usa `POST /checkout/online` con `tipo_entrega=PICKUP`.

---

### Requirement: Cálculo del total con costo de envío fijo v1

**Reason**: el cálculo del total migra a `CheckoutService` (server-side, D11), preservando exactamente la misma fórmula y los mismos valores fijos.

**Migration**: el requirement "Validación server-side de carrito" en `checkout/spec.md` preserva este comportamiento.

---

### Requirement: Anti-smuggling — campos privilegiados rechazados

**Reason**: la regla `extra="forbid"` se aplica a los nuevos schemas de checkout. Mismo comportamiento, distinto schema.

**Migration**: el requirement "Schemas Pydantic estrictos (extra=forbid)" en `checkout/spec.md` cubre este comportamiento.

---

### Requirement: Validaciones Pydantic estrictas del request

**Reason**: las validaciones (`min_length=1`, `cantidad >= 1`, etc.) se replican en los schemas de checkout.

**Migration**: `CheckoutOnlineRequest` y `CheckoutPickupEfectivoRequest` declaran las mismas validaciones.

---

### Requirement: Autenticación y autorización CLIENT obligatorias

**Reason**: ambos endpoints de checkout requieren auth CLIENT.

**Migration**: el requirement "Autenticación CLIENT obligatoria en ambos endpoints" en `checkout/spec.md` cubre este comportamiento.

---

### Requirement: Personalización opcional de items (INTEGER[])

**Reason**: el campo `personalizacion: list[int] | None` por item se mantiene en `CheckoutItem`, con el mismo comportamiento.

**Migration**: `CheckoutItem` en `checkout/schemas.py` declara `personalizacion: list[int] | None = None`.

---

### Requirement: Schema PedidoRead compacto en la respuesta

**Reason**: la respuesta del nuevo endpoint cambia — `POST /checkout/online` devuelve `CheckoutOnlineResponse` con `pedido_id`, `pago_id`, `mp_status`, `mp_id`, `status_detail`. `POST /checkout/pickup-efectivo` devuelve `CheckoutPickupEfectivoResponse` con `pedido_id`. El consumidor que necesite el detalle completo del pedido lo obtiene via `GET /api/v1/pedidos/{id}` (capability `order-visualization`, sin cambios).

**Migration**: el front lee `pedido_id` del response del checkout y, si necesita más datos, llama a `GET /pedidos/{id}`.
