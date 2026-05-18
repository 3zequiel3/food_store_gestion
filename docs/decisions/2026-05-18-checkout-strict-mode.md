# D3 — Modo estricto MP: solo `approved` crea pedido

**Fecha:** 2026-05-18  
**Change:** checkout-pay-first-flow  
**Estado:** Aceptado

## Contexto

La spec `payments-checkout-api` (recién archivada el 2026-05-17) establecía un contrato "200 OK con cualquier mp_status como dato" — un diseño defensivo que asumía que pagos `pending`/`in_process` eran legítimos y requerían seguimiento.

Sin embargo, la operativa real de un local pequeño no soporta "pedido condicionado a confirmación bancaria diferida". El cocinero necesita saber si arranca o no.

## Decisión

Si MP devuelve cualquier `status != "approved"` (incluyendo `pending`, `in_process`, `rejected`, `cancelled`, `refunded`, etc.), `POST /checkout/online` **NO crea pedido** y devuelve `402 Payment Required` con `mp_status`, `status_detail` y un mensaje user-friendly.

Si MP no responde, `502 Bad Gateway` con `code="mp_unreachable"` — tampoco crea pedido.

## Alternativas consideradas

### (a) Aceptar `pending`/`in_process` como "pedido en revisión"

Crear pedido en `PENDIENTE` con `Pago.mp_status="pending"` y esperar el webhook.

**Rechazada porque:**
- Agrega operativa de seguimiento (¿qué hace el local con un pedido en revisión? ¿cocina o espera?)
- Requiere lógica de timeout (si el webhook nunca llega, ¿el pedido se cancela?)
- Requiere notificación al cliente cuando el pago final llega
- Ensucia "Mis pedidos" con pedidos que pueden nunca confirmarse

### (b) Modo estricto (elegida)

**Ventajas:**
- Cero ambigüedad operativa: todo pedido en la DB está pagado
- "Mis pedidos" solo muestra pedidos reales
- Métricas limpias (sin pedidos fantasmas)
- Simplicidad: sin estados intermedios, sin reconciliación compleja

**Costos aceptados:**
- Pérdida de ventas "en revisión" genuinas (clientes cuyo pago queda pending temporalmente)
- El webhook MP se mantiene como red de seguridad para casos excepcionales, pero no es parte del happy path

## Rationale (decisión de producto)

La operativa real de un local pequeño **no soporta** "pedido condicionado a confirmación bancaria diferida". El cocinero necesita saber si arranca o no. Cualquier pago no inmediato se trata como rechazo desde el punto de vista del flow — el cliente reintenta o usa otra tarjeta o cambia a pickup+efectivo.

El webhook MP se mantiene como red de seguridad para reconciliar casos excepcionales (transición fallida post-cobro, pagos retrasados por MP que finalmente aprueban), pero **no es parte del happy path**.

## Impacto

### Backend
- `CheckoutService.crear_pedido_online`: solo crea pedido si `mp_status == "approved"`
- `POST /checkout/online`: retorna 402 para cualquier otro status
- Webhook MP: se mantiene pero con menos casos (ya no entran pagos `pending`/`in_process` desde el endpoint principal)

### Frontend
- `useCheckoutOnline`: maneja 402 con toast claro ("Pago rechazado", "Pago en revisión", etc.)
- OrderConfirmationPage: solo se muestra si el pago fue aprobado

### Datos
- Cero pedidos huérfanos por construcción
- Cero pedidos en `pending` limbo

## Trade-off explícito

**Operativa simple > completitud de ventas**

Se aceptan perder ventas "en revisión" a cambio de:
- Cero ambigüedad operativa
- Cero pedidos fantasmas
- Cero lógica de timeout/reconciliación compleja

Si en el futuro la operativa lo justifica (ej: alto volumen de pagos pending que finalmente aprueban), este change tiene un sucesor natural `checkout-pending-review` que reintroduce el camino.

## Referencias

- Spec: `openspec/specs/checkout/spec.md` (nueva)
- Implementación: `backend/features/checkout/service.py` — `crear_pedido_online()`
- Frontend: `frontend/src/features/checkout/hooks/useCheckoutOnline.ts`
