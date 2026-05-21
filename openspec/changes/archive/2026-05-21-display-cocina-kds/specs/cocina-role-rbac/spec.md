# Spec Delta: cocina-role-rbac

## ADDED Requirements

### Requirement: Rol COCINA en el catálogo de roles

El sistema SHALL incluir un rol `COCINA` (`Rol(codigo='COCINA', nombre='Cocinero')`) en el catálogo de roles, insertado de forma idempotente en el seed (`ON CONFLICT DO NOTHING`). La relación usuario↔rol SHALL seguir siendo N:M vía `UsuarioRol`, permitiendo que un usuario tenga `COCINA` junto a otros roles. El seed de desarrollo SHALL incluir un usuario de prueba `cocina@foodstore.com` con rol `COCINA`.

#### Scenario: Seed crea el rol COCINA idempotentemente
- **WHEN** se ejecuta el seed
- **THEN** existe un registro `Rol` con `codigo='COCINA'` y `nombre='Cocinero'`

#### Scenario: Re-ejecutar el seed no duplica el rol
- **GIVEN** el rol `COCINA` ya presente
- **WHEN** se vuelve a ejecutar el seed
- **THEN** sigue existiendo un único registro `COCINA` sin error

### Requirement: Autorización de COCINA por transición en el dominio

El sistema SHALL autorizar al rol `COCINA` exclusivamente en las transiciones de cocina `CONFIRMADO → EN_PREPARACION` y `EN_PREPARACION → TERMINADO`, declaradas en `TRANSITION_ROLES` del módulo `state_machine.py`. Cualquier otra transición solicitada por un usuario cuyo único rol relevante sea `COCINA` (por ejemplo `TERMINADO → EN_CAMINO`, `→ ENTREGADO`, o cualquier cancelación) MUST ser rechazada con HTTP 403 por `validate_transition()`, aunque el `require_role` del endpoint le permita el acceso (RN-CO03). La autorización por transición vive en el dominio, no solo en el borde HTTP.

#### Scenario: COCINA inicia preparación
- **WHEN** un usuario con rol `COCINA` ejecuta la transición `CONFIRMADO → EN_PREPARACION`
- **THEN** la transición se ejecuta sin error

#### Scenario: COCINA marca terminado
- **WHEN** un usuario con rol `COCINA` ejecuta la transición `EN_PREPARACION → TERMINADO`
- **THEN** la transición se ejecuta sin error

#### Scenario: COCINA no puede despachar
- **WHEN** un usuario con solo rol `COCINA` intenta la transición `TERMINADO → EN_CAMINO`
- **THEN** la respuesta es 403 (`COCINA` no está en `TRANSITION_ROLES` de esa transición)

#### Scenario: COCINA no puede cancelar
- **WHEN** un usuario con solo rol `COCINA` intenta cancelar un pedido en `EN_PREPARACION`
- **THEN** la respuesta es 403

### Requirement: Auditoría de avances ejecutados por cocina

El sistema SHALL registrar cada transición ejecutada por un cocinero en `HistorialEstadoPedido` (append-only) con `estado_anterior_codigo`, `estado_nuevo_codigo`, `cambiado_por_id` igual al id del cocinero y `creado_en` (RN-CO04, RN-FS07). El sistema MUST NOT ejecutar UPDATE ni DELETE sobre `HistorialEstadoPedido`.

#### Scenario: Avance de cocina queda auditado
- **WHEN** un cocinero ejecuta `EN_PREPARACION → TERMINADO`
- **THEN** se inserta una fila en `order_state_history` con `estado_anterior_codigo="EN_PREPARACION"`, `estado_nuevo_codigo="TERMINADO"` y `cambiado_por_id` igual al id del cocinero

#### Scenario: El historial nunca se actualiza ni borra
- **WHEN** se inspecciona el modelo `HistorialEstadoPedido`
- **THEN** hereda de `AppendOnlyBaseModel` y no admite UPDATE ni DELETE a nivel ORM
