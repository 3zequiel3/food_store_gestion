# Delta for order-visualization-frontend

## MODIFIED Requirements

### Requirement: Modal de Detalle de Pedido

El sistema SHALL mostrar un `OrderDetailModal` al hacer click en cualquier pedido, tanto en la vista CLIENT como en la PEDIDOS/ADMIN. El modal MUST mostrar: ítems del pedido (nombre, cantidad, precio snapshot, subtotal), timeline de historial de estados con fechas, datos de pago (forma de pago con labels frontend alineados al backend; `TARJETA` se renderiza como "Tarjeta", y estado del pago si existe) y dirección snapshot. Los estados cancelados SHALL conservar labels diferenciados si el backend devuelve `CANCELADO_ADMIN` o `CANCELADO_CLIENTE`. (Previously: el modal no tenía label para `TARJETA`.)

#### Scenario: Modal muestra ítems con precio snapshot
- WHEN el usuario hace click en un pedido
- THEN el modal muestra cada ítem con su precio al momento de la compra (`precio_snapshot`)

#### Scenario: Modal muestra timeline de estados
- WHEN el modal está abierto
- THEN se muestra el historial de estados en orden cronológico con fechas

#### Scenario: Modal muestra forma de pago migrada
- WHEN el pedido tiene `forma_pago_codigo="TARJETA"`
- THEN el modal renderiza el texto "Tarjeta"

#### Scenario: Cerrar modal con Escape o botón
- WHEN el usuario presiona Escape o el botón de cierre
- THEN el modal se cierra y la lista queda visible

### Requirement: OrderStatusBadge

El sistema SHALL exponer un componente `OrderStatusBadge` que recibe un `estado_codigo` y renderiza un badge con color semántico: `PENDIENTE` → warning, `CONFIRMADO` → info, `EN_PREPARACION` → primary, `TERMINADO` → listo para retirar/entregar, `ENTREGADO` → success, y cualquier estado cancelado (`CANCELADO`, `CANCELADO_ADMIN`, `CANCELADO_CLIENTE`) → destructive con label en español. (Previously: los subtipos cancelados caían al fallback neutral y `CANCELADO` tenía variante neutral.)

#### Scenario: Badge muestra color correcto por estado entregado
- WHEN `OrderStatusBadge` recibe `estado_codigo="ENTREGADO"`
- THEN renderiza un badge verde con el texto "Entregado"

#### Scenario: Badge muestra cancelación de admin en rojo
- WHEN `OrderStatusBadge` recibe `estado_codigo="CANCELADO_ADMIN"`
- THEN renderiza un badge destructive con un label explícito de cancelación administrativa

#### Scenario: Badge muestra cancelación de cliente en rojo
- WHEN `OrderStatusBadge` recibe `estado_codigo="CANCELADO_CLIENTE"`
- THEN renderiza un badge destructive con un label explícito de cancelación del cliente

#### Scenario: Badge muestra label en español
- WHEN el estado es cualquier código válido soportado por la UI
- THEN el label se muestra en español y distingue los subtipos de cancelación cuando aplica
