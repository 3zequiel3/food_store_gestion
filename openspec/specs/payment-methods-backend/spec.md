## Purpose

Endpoint público (autenticado) para listar formas de pago habilitadas. El frontend lo necesita para el selector de forma de pago en el checkout. Gap detectado: no existía endpoint para listar `payment_methods`.

## ADDED Requirements

### Requirement: Listar formas de pago habilitadas

El sistema SHALL exponer `GET /api/v1/formas-pago` protegido por `Depends(get_current_user)` (cualquier rol autenticado) que devuelve `200 OK` con una lista de `FormaPagoRead` objects filtrados por `habilitada=True`, ordenados por `id` ascendente. (US-035 — selección de forma de pago)

#### Scenario: Listar formas de pago habilitadas
- **WHEN** un usuario autenticado envía `GET /api/v1/formas-pago`
- **THEN** responde `200 OK` con una lista de formas de pago donde `habilitada=true`
- **AND** cada item tiene `codigo`, `descripcion` y `habilitada`

#### Scenario: Formas deshabilitadas excluidas
- **GIVEN** existe una forma de pago con `codigo="EFECTIVO"` y `habilitada=false`
- **WHEN** se lista las formas de pago
- **THEN** EFECTIVO no aparece en la respuesta

#### Scenario: Request sin autenticación responde 401
- **WHEN** un usuario anónimo envía `GET /api/v1/formas-pago`
- **THEN** responde `401 Unauthorized`

#### Scenario: FormaPagoRead schema
- **WHEN** se lista una forma de pago
- **THEN** el response tiene la forma `{ codigo: string, descripcion: string, habilitada: boolean }`
- **AND** no expone campos internos como `id`