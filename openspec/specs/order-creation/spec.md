# order-creation — Spec vigente

Capability para crear pedidos desde el carrito del cliente, con validación de stock, forma de pago, dirección y snapshots inmutables.

---

## Requirements

> **DEPRECATED**: Este spec ha sido reemplazado por la capability `checkout`. Todas las operaciones de creación de pedidos (online y pickup) ahora pasan por `POST /api/v1/checkout/online` o `POST /api/v1/checkout/pickup-efectivo` (capability `checkout`). Los requirements originales (Crear pedido desde el carrito, Snapshots, Validación de stock, etc.) migran a `checkout/spec.md`.
>
> Consultar `openspec/changes/checkout-pay-first-flow/specs/order-creation/spec.md` para ver el análisis completo de qué se removió y por qué.

---

_(Todos los requirements han sido migrados a la capability `checkout`. Ver sección "DEPRECATED" arriba.)_
