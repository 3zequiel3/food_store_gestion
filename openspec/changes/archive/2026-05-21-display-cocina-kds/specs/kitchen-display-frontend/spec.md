# Spec Delta: kitchen-display-frontend

## ADDED Requirements

### Requirement: Tablero Kanban del KDS en /cocina

El sistema SHALL renderizar en la ruta `/cocina` un tablero Kanban con dos columnas: "Por preparar" (pedidos en `CONFIRMADO`) y "En preparación" (pedidos en `EN_PREPARACION`). Cada tarjeta SHALL mostrar el número de pedido, los ítems (`nombre_snapshot` × `cantidad`), las exclusiones de `personalizacion` y las `notas` del cliente. El tablero SHALL cargar el estado inicial con `GET /api/v1/cocina/pedidos` y ordenar los pedidos por antigüedad ascendente (RN-CO02).

#### Scenario: Dos columnas por estado
- **WHEN** un cocinero autenticado entra a `/cocina`
- **THEN** ve la columna "Por preparar" con pedidos `CONFIRMADO` y la columna "En preparación" con pedidos `EN_PREPARACION`

#### Scenario: Tarjeta muestra ítems, exclusiones y notas
- **GIVEN** un pedido con ítems, una exclusión de ingrediente y una nota del cliente
- **WHEN** se renderiza su tarjeta en el KDS
- **THEN** la tarjeta muestra los ítems con cantidad, las exclusiones y la nota

#### Scenario: Ver detalle muestra producto e ingredientes
- **WHEN** el cocinero abre "Ver detalle" de una tarjeta
- **THEN** ve el producto y sus ingredientes

### Requirement: Acciones de avance del cocinero

El sistema SHALL ofrecer en cada tarjeta las acciones de avance correspondientes al estado: "Iniciar preparación" para pedidos en `CONFIRMADO` (`CONFIRMADO → EN_PREPARACION`) y "Terminado" para pedidos en `EN_PREPARACION` (`EN_PREPARACION → TERMINADO`). Cada acción SHALL invocar el endpoint de transición de estado; el resultado SHALL reflejarse en el tablero (mover la tarjeta o retirarla).

#### Scenario: Iniciar preparación mueve la tarjeta
- **WHEN** el cocinero presiona "Iniciar preparación" en un pedido `CONFIRMADO`
- **THEN** la tarjeta se mueve a la columna "En preparación"

#### Scenario: Terminado retira la tarjeta
- **WHEN** el cocinero presiona "Terminado" en un pedido `EN_PREPARACION`
- **THEN** la tarjeta desaparece del tablero

### Requirement: Actualización en tiempo real vía WebSocket

El sistema SHALL abrir el WebSocket `WS /api/v1/cocina/ws` al montar el KDS y reaccionar a los eventos para agregar, mover o retirar tarjetas sin recargar la página. `pedido_confirmado` agrega una tarjeta en "Por preparar"; `pedido_en_preparacion` la mueve a "En preparación"; `pedido_terminado` y `pedido_cancelado` la retiran del tablero.

#### Scenario: Pedido nuevo aparece sin recargar
- **GIVEN** el KDS abierto con WebSocket conectado
- **WHEN** llega un evento `pedido_confirmado`
- **THEN** aparece una tarjeta nueva en "Por preparar" sin recargar

#### Scenario: Pedido terminado en otra pantalla desaparece
- **GIVEN** dos pantallas de cocina conectadas
- **WHEN** un cocinero marca un pedido como terminado en una pantalla
- **THEN** la tarjeta desaparece de ambas pantallas

### Requirement: Resiliencia con fallback por polling

El sistema SHALL mostrar un indicador de "sin conexión en vivo" cuando el WebSocket se desconecte y SHALL activar polling de `GET /api/v1/cocina/pedidos` cada 30 segundos como fallback. Al reconectar el WebSocket, el sistema SHALL volver al modo push y refrescar el estado completo.

#### Scenario: Polling al caer el WebSocket
- **WHEN** el WebSocket se desconecta
- **THEN** el KDS muestra el indicador de "sin conexión en vivo" y consulta `GET /api/v1/cocina/pedidos` cada 30 segundos

#### Scenario: Vuelve al push al reconectar
- **WHEN** el WebSocket reconecta
- **THEN** el KDS deja de hacer polling, refresca el estado completo y vuelve a recibir eventos por push

### Requirement: Timer de urgencia por tiempo de espera

El sistema SHALL mostrar en cada tarjeta el tiempo transcurrido desde la entrada del pedido a `CONFIRMADO`, recalculado en el cliente cada 15 segundos. El estilo SHALL ser normal para < 10 minutos, de advertencia (naranja) para 10–20 minutos, y urgente (rojo) para > 20 minutos (RN-CO07).

#### Scenario: Umbral de advertencia
- **GIVEN** un pedido que entró a cocina hace 12 minutos
- **WHEN** se renderiza su tarjeta
- **THEN** el timer se muestra con estilo de advertencia (naranja)

#### Scenario: Umbral urgente
- **GIVEN** un pedido que entró a cocina hace 25 minutos
- **WHEN** se renderiza su tarjeta
- **THEN** el timer se muestra con estilo urgente (rojo)

#### Scenario: Recalculo periódico sin recargar
- **WHEN** transcurren 15 segundos con el KDS abierto
- **THEN** los timers de las tarjetas se actualizan sin recargar la página

### Requirement: Vista exclusiva y persistencia del rol cocinero

El sistema SHALL redirigir a un usuario con rol `COCINA` a `/cocina` como única vista tras el login, sin exponerle el resto del shell de la aplicación. La ruta `/cocina` SHALL quedar excluida del auto-logout por inactividad, de modo que la pantalla permanezca activa durante el turno.

#### Scenario: Login COCINA aterriza en /cocina
- **WHEN** un usuario con rol `COCINA` inicia sesión
- **THEN** es redirigido a `/cocina` y no ve la navegación del resto de la app

#### Scenario: /cocina no dispara auto-logout por inactividad
- **GIVEN** el auto-logout por inactividad activo en el resto de la app
- **WHEN** el usuario está en `/cocina` sin interacción
- **THEN** la sesión no se cierra por inactividad

### Requirement: Alerta de pedido entrante (opcional)

El sistema SHALL, al recibir `pedido_confirmado`, poder reproducir un aviso sonoro (Web Audio API, sin archivos externos) y un flash visual breve, controlado por un toggle de sonido ON/OFF persistente en `localStorage`. El aviso sonoro depende de una interacción previa del usuario con la página (política de autoplay del navegador), límite que SHALL documentarse.

#### Scenario: Toggle de sonido persiste
- **WHEN** el cocinero apaga el sonido y recarga la página
- **THEN** el toggle permanece apagado (persistido en `localStorage`)

#### Scenario: Flash visual al llegar un pedido
- **WHEN** llega un evento `pedido_confirmado`
- **THEN** el KDS hace un flash visual breve
