## Context

El módulo de pagos integra MercadoPago vía Checkout API inline. El flujo actual de `POST /api/v1/pagos/` (ver `backend/features/payments/service.py:40-199`) ejecuta cinco fases:

1. **Phase 1** (UoW read-only): valida pedido del usuario, estado `PENDIENTE`, y no-pago-activo (`find_active_by_pedido_id` busca `mp_status ∈ {"approved","pending","in_process"}`).
2. **Phase 2** (sin DB): llama `sdk.payment().create(payment_data, request_options)`.
3. **Phase 3** (UoW write): re-chequea active payment (race guard), llama `repository.create_pago(...)` que inserta con `mp_status="pending"` por default, y si MP devolvió `mp_payment_id` llama `update_mp_fields(...)`. El UoW commitea al `__exit__`.
4. **Phase 4**: si MP no devolvió status o devolvió error → `raise BusinessRuleError(code="payment_error")`. Si status == `"approved"` → transiciona el pedido y retorna dict. Cualquier otro status → `raise BusinessRuleError(code=f"payment_{mp_status}")`.

El problema central es que **Phase 3 ya commiteó el `Pago` cuando Phase 4 levanta excepción**. La consecuencia depende del status:

- **MP error sin status**: queda `Pago(mp_status="pending", mp_payment_id=None)`. `pending` está en `_ACTIVE_STATUSES` → todo reintento futuro choca con "Ya existe un pago activo". **Bloqueo permanente sin intervención DB.**
- **MP devuelve `rejected`**: queda `Pago(mp_status="rejected", mp_payment_id="123")`. `rejected` NO está en `_ACTIVE_STATUSES` → reintentos funcionan. Comportamiento aceptable de fondo, pero el front no se entera porque recibe 422.
- **MP devuelve `pending`**: queda `Pago(mp_status="pending", ...)`. Correcto que bloquee reintentos (es el mismo pago en revisión). Pero el front muestra "Estado de pago inesperado" en vez de "Tu pago está en revisión".

El front (`PaymentForm.tsx:33-40`) está escrito esperando 200 OK con `mp_status` como dato. Hay disonancia de contrato: backend modela como excepción, frontend espera como dato. Resultado: el `else` del front (statuses que no son `approved`/`rejected`/`cancelled`) nunca se ejecuta porque el backend ya rechazó con 422, y el front cae al `catch(err)` con mensajes genéricos.

Constraints heredados del proyecto:

- **Regla de oro de imports**: repository → models, shared. Service → repository, shared. Router → service, schemas. No saltearlo.
- **UoW**: toda operación multi-tabla envuelta en `with UnitOfWork() as uow`.
- **Pydantic v2** con `ConfigDict(extra="forbid")` para requests.
- **Strict TDD activado**: test primero, después implementación.
- **No se toca el webhook handler** — `procesar_webhook` ya está bien.

Stakeholders: el front (único cliente del API), el módulo de orders (consumidor de la transición `PENDIENTE→CONFIRMADO`), el módulo de auditoría (espera logs de errores en transiciones).

## Goals / Non-Goals

**Goals:**

- Que `POST /api/v1/pagos/` devuelva 200 OK con `mp_status` real cualquiera sea el resultado de MP, mientras MP haya respondido.
- Que cuando MP NO responda (timeout, 5xx, token inválido) se devuelva 502 `mp_unreachable` y **no se cree ningún Pago** en la DB.
- Que el `Pago` se persista con el `mp_status` real desde el primer write, eliminando el riesgo del default `"pending"` que bloquea reintentos cuando en realidad MP no procesó nada.
- Que el frontend distinga semánticamente cuatro categorías de resultado: éxito, en revisión, rechazo, error inesperado — y muestre mensajes user-friendly en castellano rioplatense para cada caso.
- Que los errores silenciados (`except Exception: pass` en la transición) queden en logs estructurados.
- Borrar todo el código muerto del flow wallet legacy (`initiatePayment`, `useInitPayment`, `PagoCreate` interface).

**Non-Goals:**

- No se implementa polling automático de pagos en `pending` (queda para `payments-pending-polling`).
- No se cambia el webhook handler — su lógica está bien.
- No se corrige el TOCTOU entre `find_active_by_pedido_id` y `create_pago` (requiere `SELECT FOR UPDATE`, va en otro change).
- No se cambia el contrato de `GET /api/v1/pagos/pedido/{id}` — sigue devolviendo `PagoRead`. La alineación va en otro change.
- No se valida el `forma_pago_codigo` del body (hoy se hardcodea `"TARJETA"` en el service). Queda para otro change.
- No se agrega verificación HMAC del webhook.
- No se agrega seed o data migration — el modelo `Pago` y `_ACTIVE_STATUSES` ya están correctos.

## Decisions

### D1: Devolver 200 OK para cualquier status que MP haya respondido — incluido `rejected` y `cancelled`

**Decisión**: el endpoint devuelve `200 OK` con el body `PagoCreateResponse` siempre que MP haya respondido con un `status`, sin importar cuál sea. Solo se levanta excepción cuando MP NO devolvió status (= no podemos saber qué pasó con el pago).

**Alternativas consideradas:**

- **A. Status quo (raise 422 para no-approved)**: rompe el contrato esperado por el front, fuerza al cliente a parsear `error.code` para entender el resultado, y mezcla "error de regla de negocio" con "resultado válido de un pago". Rechazada.
- **B. Devolver 200 solo para `approved` y `pending`, 422 para `rejected`/`cancelled`**: arbitrario. ¿Por qué un `pending` es "ok" y un `rejected` es "error"? Ambos son resultados informativos de MP. Rechazada.
- **C. (elegida) Devolver 200 OK para cualquier status MP, 502 cuando MP no responde**: trata "el banco rechazó" como dato (es informativo, no un error del servidor ni del usuario), y "MP no contestó" como falla de upstream (502 es semánticamente correcto). El front decide qué hacer con cada caso.

**Rationale**: en MercadoPago Checkout API, el `status` del payment ES el resultado de la operación. Un rechazo del banco no es un error HTTP — es un dato. La práctica estándar de las pasarelas (Stripe `payment_intent.status`, Adyen `resultCode`, MP mismo) es devolver el status como campo del response y dejar al cliente clasificarlo. Esto es lo que el front ya asumía implícitamente.

### D2: Mover la creación del `Pago` ADENTRO del branch "MP devolvió status"

**Decisión**: refactor de `crear_pago_api` para que Phase 3 ocurra solo en el camino "MP respondió con status". Si MP no respondió, se sale antes del UoW de write con un `raise BusinessRuleError(code="mp_unreachable")` y la DB no se toca.

```
Phase 1: Validar pedido + no-pago-activo (UoW read).
Phase 2: Llamar MP.
Phase 3 (NUEVO branching):
   if not mp_status:
       raise BusinessRuleError(code="mp_unreachable")  # 502, sin tocar DB
   else:
       UoW write: re-chequear active, create_pago(mp_status=<real>), update_mp_fields si hay mp_payment_id
Phase 4: si mp_status == "approved" → transicionar pedido (con logging real en lugar de pass).
Phase 5: return PagoCreateResponse.
```

**Alternativas consideradas:**

- **A. Mantener `create_pago` siempre y borrar el Pago si MP erroreó**: requiere UoW de compensación (insert + commit + delete + commit), introduce ventanas de inconsistencia, y deja registros fantasma en logs/auditoría. Rechazada.
- **B. Mover `create_pago` a Phase 4 dentro del `if approved`**: pierde el registro de pagos rechazados/cancelados, que es información útil para el cliente y para reporting. Rechazada.
- **C. (elegida) `create_pago` solo si MP devolvió status (cualquier status), y el status real se pasa al insert**: persiste todos los intentos con resultado conocido, no persiste los intentos donde MP no contestó. `rejected` y `cancelled` quedan en DB pero NO en `_ACTIVE_STATUSES`, así que no bloquean reintentos. `pending` e `in_process` quedan en `_ACTIVE_STATUSES` (correcto: hay un pago en curso real con MP).

### D3: Pasar `mp_status` como argumento explícito a `repository.create_pago(...)`

**Decisión**: cambiar la firma de `PaymentRepository.create_pago` para aceptar `mp_status: str` opcional con default `"pending"` (compat). El service siempre lo pasa explícito con el valor real devuelto por MP.

**Alternativas consideradas:**

- **A. Dejar el default `"pending"` y llamar `update_mp_fields` inmediatamente después**: requiere dos writes en la misma transacción, complica los tests, y deja la fila brevemente en un estado incorrecto antes del flush. Rechazada.
- **B. (elegida) Aceptar `mp_status` como parámetro de `create_pago`**: un solo write, intent claro en el service, repository sigue tonto (data access puro).

**Compatibilidad**: el webhook handler no usa `create_pago`, así que no hay impacto. Los tests existentes que llamaran `create_pago(...)` sin `mp_status` siguen funcionando porque el default es `"pending"` (cobertura legacy).

### D4: `PagoCreateResponse` incluye `pago_id`

**Decisión**: el response del endpoint incluye `pago_id: int` (nuestro ID interno) además de `mp_status`, `mp_id`, `status_detail`.

**Alternativas consideradas:**

- **A. No incluir `pago_id`, el front pollea por `pedido_id` vía `GET /pagos/pedido/{id}`**: funciona pero es indirecto. El front ya sabe el `pedido_id`, no agrega información.
- **B. (elegida) Incluir `pago_id`**: facilita la futura ruta `GET /pagos/{pago_id}` (más directa que la lookup por pedido), no rompe nada, costo cero. El polling principal sigue siendo por `pedido_id` para mantener consistencia con `usePaymentByOrder`.

### D5: Mapear `mp_unreachable` a 502 via handler explícito

**Decisión**: agregar handling en `shared/exceptions.py` (o el handler global, depende de cómo esté estructurado el proyecto) para que `BusinessRuleError(code="mp_unreachable")` se mapee a HTTP 502 en lugar del 422 por default.

**Alternativas consideradas:**

- **A. Crear nueva excepción `UpstreamError`**: más explícito pero requiere tocar varios archivos. Si el proyecto solo tiene esto como un caso aislado, agregar una excepción nueva por un solo caso es over-engineering.
- **B. (elegida) Reutilizar `BusinessRuleError` con `code="mp_unreachable"` y mapear en el handler**: si el handler global usa el `code` para decidir status HTTP (patrón común en FastAPI), es un cambio de una línea. Si el handler global devuelve 422 hardcoded, se introduce una `UpstreamError` minimal subclase. La elección final se valida en la primera task de tasks.md ("Inspeccionar `shared/exceptions.py` y handler global").

### D6: `PaymentForm` clasifica statuses en 4 buckets, expone `onPending`

**Decisión**: agregar prop `onPending` al `PaymentFormProps`. La lógica del componente clasifica:

```ts
const TERMINAL_SUCCESS = ['approved'] as const;
const PENDING_REVIEW = ['pending', 'in_process', 'authorized'] as const;
const TERMINAL_FAILURE = ['rejected', 'cancelled'] as const;
// el resto → onError genérico con status_detail

if (TERMINAL_SUCCESS.includes(response.mp_status)) onSuccess(response);
else if (PENDING_REVIEW.includes(response.mp_status)) onPending(response, friendlyMessage);
else if (TERMINAL_FAILURE.includes(response.mp_status)) onError(friendlyMessage);
else onError(response.status_detail ?? `Resultado inesperado: ${response.mp_status}`);
```

`friendlyMessage` viene de `statusDetailMessages[response.status_detail]` con fallback al `status_detail` crudo si no hay mapeo.

**Alternativas consideradas:**

- **A. Una sola callback `onResult(category, message, response)` con switch en el caller**: más DRY pero introduce un nuevo tipo de discriminante, los callers tienen que importar el enum, y el cambio se propaga a todos los lugares que usan `PaymentForm`. Para un solo caller (`PaymentPage`) es over-engineering.
- **B. (elegida) Tres callbacks separadas `onSuccess` / `onPending` / `onError`**: TypeScript hace el matching obvio, cada caller maneja solo lo que le importa. Idiomatic React.

### D7: `statusDetailMessages.ts` como constante simple, no i18n

**Decisión**: archivo plano con un objeto `Record<string, string>` exportado. No se introduce framework de i18n.

```ts
export const statusDetailMessages: Record<string, string> = {
  cc_rejected_insufficient_amount: 'Saldo insuficiente. Probá con otra tarjeta.',
  cc_rejected_bad_filled_security_code: 'CVV incorrecto. Revisá el código de seguridad.',
  cc_rejected_bad_filled_card_number: 'Número de tarjeta incorrecto.',
  cc_rejected_bad_filled_date: 'Fecha de vencimiento incorrecta.',
  cc_rejected_other_reason: 'Tarjeta rechazada. Probá con otra.',
  cc_rejected_call_for_authorize: 'Tenés que autorizar el pago con tu banco.',
  cc_rejected_high_risk: 'Pago rechazado por seguridad. Probá con otra tarjeta.',
  pending_review_manual: 'Tu pago está en revisión. Te avisaremos cuando se confirme.',
  pending_waiting_payment: 'Tu pago está pendiente de procesamiento.',
  accredited: 'Pago aprobado.',
};

export function friendlyMessageFor(statusDetail: string | null | undefined): string {
  if (!statusDetail) return 'Sin información adicional.';
  return statusDetailMessages[statusDetail] ?? statusDetail;
}
```

**Alternativas consideradas:**

- **A. i18n con `react-i18next` o similar**: el proyecto no usa i18n hoy, agregarlo por este caso es over-engineering.
- **B. (elegida) Constante simple + función helper**: testable, extensible, alineado con el resto del front.

### D8: Logging del fallo de transición usa el logger del módulo

**Decisión**: reemplazar `except Exception: pass` por:

```python
except Exception:
    logger.exception(
        "Fallo al transicionar pedido %s a CONFIRMADO tras pago aprobado %s. "
        "El webhook intentará reconciliarlo.",
        pedido_id,
        mp_payment_id,
    )
```

No se re-raise: el pago YA está aprobado y persistido. El webhook va a hacer la transición en segundo intento. Re-raise convertiría un cobro exitoso en un error 5xx para el cliente, lo cual es peor UX.

**Alternativas consideradas:**

- **A. Re-raise**: el front recibe error, pero el cargo ya se hizo. Confuso. Rechazada.
- **B. `pass` silencioso (status quo)**: pierde traza de fallos. Rechazada.
- **C. (elegida) `logger.exception(...)` sin re-raise**: traza completa en logs, sin afectar al cliente, webhook como red de seguridad.

### D9: `PaymentPage` muestra estado de pending inline, sin polling

**Decisión**: cuando `PaymentPage` recibe `onPending(response, message)`, renderiza un panel con:

- Ícono de reloj (lucide `Clock`).
- Mensaje user-friendly (`message`).
- Texto secundario "Te avisaremos por mail cuando se confirme el pago" (asumiendo el webhook eventualmente actualiza el estado).
- Botón "Ver estado del pedido" → `navigate(\`/cliente/pedidos/${pedidoId}/confirmacion\`)`.

No se implementa polling automático en este change. El usuario puede refrescar manualmente o esperar la notificación.

**Alternativas consideradas:**

- **A. Polling con `setInterval` + backoff**: requiere manejo de cleanup, retries, error states. Es un mini-feature en sí mismo. Se difiere a `payments-pending-polling`.
- **B. (elegida) Vista estática con CTA explícito**: simple, funcional, no bloquea este change.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| Tests del backend asumen 422 para no-approved → suite roja al inicio del refactor | TDD: actualizar tests primero (RED), luego cambiar el service (GREEN). Tarea explícita en `tasks.md`. |
| `BusinessRuleError(code="mp_unreachable")` no se mapea automáticamente a 502 → devuelve 422 | Primera task de backend: auditar `shared/exceptions.py` y decidir entre (a) mapping en handler global o (b) nueva subclase `UpstreamError`. Decisión documentada en el commit que la implemente. |
| El front-end maneja `onPending` pero el usuario no entiende qué hacer → UX confusa | El mensaje fijo "Te avisaremos por mail..." + botón explícito a `/cliente/pedidos/{id}/confirmacion` da un siguiente paso claro. Polling completo queda como follow-up. |
| Cambiar el shape del response del POST puede romper tests del frontend que mockean `createInlinePayment` | Tests del front también van a RED primero (TDD), luego refactor del componente. Cubierto en tasks.md. |
| Algún test del back llama `repository.create_pago(...)` sin `mp_status` | El default `"pending"` mantiene retrocompatibilidad. Si algún test falla, se actualiza puntualmente. |
| Decisión D5 puede requerir más cambios de los esperados si `shared/exceptions.py` no tiene patrón de `code → status` | Task 1 del backend audita esto explícitamente antes de proceder. Si requiere nueva clase, el design.md se actualiza inline durante apply. |
| El logging de D8 puede generar mucho ruido si la transición falla seguido (e.g. orders module en mantenimiento) | Aceptable: si la transición falla seguido es una señal real que hay que ver. El webhook compensa funcionalmente; los logs avisan al equipo. |
| Borrar `useInitPayment` puede romper algún import oculto | Búsqueda con `rg "useInitPayment"` antes de borrar. Tarea explícita en tasks.md. |

## Migration / Rollout

1. Branch nuevo: `change/payments-non-approved-as-data`.
2. Backend primero (TDD): tests RED → schema `PagoCreateResponse` → repository signature → service refactor → router `response_model` → logging → tests GREEN.
3. Frontend segundo (TDD): tests RED del `PaymentForm` y `PaymentPage` → `statusDetailMessages.ts` → refactor componente → refactor página → tests GREEN.
4. Borrado de código muerto al final (`initiatePayment`, `useInitPayment`, `PagoCreate` legacy) — minimiza riesgo de conflictos.
5. Validación cross-stack manual con tarjetas de test MP (sandbox): una APRUEBA, una RECHAZA, una PENDING.
6. Verificar OpenAPI en `/docs` que el response del POST esté declarado.

**Rollback**: revertir el commit. El cambio no toca migrations ni datos, así que `git revert` es seguro. `_ACTIVE_STATUSES` no cambia. Tablas no cambian.

## Open Questions

- ¿`shared/exceptions.py` ya tiene mapping `code → http_status` o devuelve 422 hardcoded para todo `BusinessRuleError`? Resolver en primera task del backend.
- ¿Hay otros consumidores de `repository.create_pago` además del service? Verificar con `rg "create_pago" backend/`.
- ¿El `OrderConfirmationPage` (target del botón de pending) maneja correctamente un pedido todavía en estado PENDIENTE? Asumido que sí — se valida durante el testing manual.
