# MercadoPago Checkout API — Research Document

**Date**: 2026-05-14
**Last Updated**: 2026-05-14 (Checkout API research added)
**Status**: Research / Planning
**Target Integration**: Food Store Backend (FastAPI) + Frontend (React)

---

## 0. Checkout API vs Checkout Pro — Decision

**We are using Checkout API** (server-side payment creation), NOT Checkout Pro.

| Aspect | Checkout Pro (old plan) | Checkout API (chosen) |
|--------|----------------------|----------------------|
| **What** | MP-hosted checkout page | Server creates payment directly |
| **Flow** | Create Preference → redirect to MP → MP processes → webhook | Browser tokenizes card (MP.js Secure Fields) → backend calls `sdk.payment().create()` → **immediate synchronous response** → webhook for async methods |
| **SDK method** | `sdk.preference().create(data)` | `sdk.payment().create(data, request_options)` |
| **User leaves site?** | YES | NO (stays on your domain) |
| **Idempotency** | N/A (preference is config) | `x-idempotency-key` header via `RequestOptions` |
| **PCI scope** | SAQ-A (easiest) | SAQ-A (token never touches your server) |
| **Return URLs** | `back_urls.*` in preference | Not needed for cards; `external_resource_url` for tickets |

### Why Checkout API?
- Full UX control — branded checkout on our domain
- Immediate card approval response (no need to wait for webhook)
- Better conversion — user never leaves the site
- Spec direction: US-045 mentions "Card tokenization with MP.js SDK"

---

## 1. Payment Creation Flow (Checkout API)

Checkout API works by creating a **Payment** directly on the MercadoPago server.

### Flow
1. Frontend uses **MP.js Secure Fields** to tokenize the card → gets a `token`
2. Frontend sends `token` + `payment_method_id` + `installments` to backend
3. Backend calls `sdk.payment().create(payment_data, request_options)`
4. MP returns the **payment object** with immediate `status`
5. Backend updates Pago record and triggers order state transition
6. Webhook arrives later as confirmation (idempotent — D5/D6 handles duplicates)

### Payment Creation — Python SDK (mercadopago 2.4.0+)

```python
import mercadopago
from mercadopago.config import RequestOptions

sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

# Idempotency key — prevents double charges on retries
request_options = RequestOptions()
request_options.custom_headers = {
    'x-idempotency-key': str(idempotency_key)  # UUID4 per Pago row
}

payment_data = {
    "transaction_amount": float(pedido.total),
    "token": card_token,           # From frontend: MP.js Secure Fields
    "description": f"Pedido #{pedido_id} — Food Store",
    "payment_method_id": payment_method,  # 'visa', 'master', 'rapipago', etc.
    "installments": installments,
    "payer": {"email": pedido.user.email},
    "external_reference": str(pedido_id),
    "notification_url": "https://foodstore.com/api/v1/pagos/webhook/mercadopago",
}

result = sdk.payment().create(payment_data, request_options)
payment = result["response"]
# payment["id"]     → mp_payment_id
# payment["status"] → 'approved'|'pending'|'in_process'|'rejected'|'cancelled'
```

### Payment Statuses
| MP Status | Action | Order Effect |
|-----------|--------|-------------|
| `approved` | Update Pago, PENDIENTE→CONFIRMADO, decrement stock | ✅ Confirmed |
| `pending` | Update Pago, order stays PENDIENTE | ⏳ Wait (ticket/offline) |
| `in_process` | Update Pago, order stays PENDIENTE | ⏳ Wait (risk review) |
| `rejected` | Update Pago, allow retry (D10) | ❌ Can retry |
| `cancelled` | Update Pago | 🚫 May cancel order |
| `refunded` | Update Pago | 💸 Refund flow |

### Integration Gap
Current backend uses `sdk.preference().create()` (Checkout Pro). Needs to switch to `sdk.payment().create()` with:
1. Accept `card_token` + `payment_method_id` from frontend
2. Add `notification_url` to payment data
3. Pass `x-idempotency-key` via `RequestOptions.custom_headers`
4. Handle synchronous response — card payments return `approved` immediately

---

## 2. Webhook IPN (Instant Payment Notification) Format

MercadoPago sends POST requests to the `notification_url` when payment status changes.

### Three Notification Formats (all handled by current backend)

| Format | Body | Query Params | Extraction |
|--------|------|-------------|------------|
| Modern webhook | `{"type":"payment","data":{"id":"123"}}` | — | `body.data.id` |
| Old IPN body | `{"topic":"payment","resource":"…/payments/123"}` | — | Regex `/payments/(\d+)` |
| Classic IPN | (empty) | `?topic=payment&id=123` | `query.id` |

**The current backend already handles all three formats** in `_extract_mp_payment_id`. No changes needed here.

### Verification is the same regardless of Checkout Pro or Checkout API:
Call `sdk.payment().get(id)` → trust API response, not the payload.

### Integration Gap
Backend webhook handler is already complete and works for both flows. ✅

---

## 3. Return URL Behavior

| Flow | Return URLs |
|------|------------|
| **Checkout Pro** | `back_urls.success/failure/pending` in preference data + `auto_return: "approved"` |
| **Checkout API (cards)** | None needed — `sdk.payment().create()` response has `status` immediately |
| **Checkout API (tickets/offline)** | `transaction_details.external_resource_url` in the payment response — URL to show the voucher (Rapipago, Pago Fácil) |

### Important Notes
- For card payments, the synchronous response is the primary source of truth
- Webhook arrives later as confirmation (idempotent)
- For ticket methods (Rapipago, Pago Fácil), the user needs to see the voucher URL

### Integration Gap
Frontend needs to handle:
- Immediate card approval → show success page
- Pending/rejected → show appropriate message
- Ticket methods → display `external_resource_url` for printing

---

## 4. Notification Polling Strategy

As a fallback or complement to webhooks, the frontend can poll for payment status:

### Approach
1. After initiating payment, store `pedido_id` locally.
2. Poll `GET /pagos/pedido/{pedidoId}` every 2-3 seconds.
3. Stop polling when status is `approved`, `rejected`, or `cancelled`.
4. Max polling attempts: ~30 (60-90 seconds), then show "contact support" message.

### Why Polling?
- Webhooks may be delayed or lost (network issues).
- User may close browser before webhook arrives.
- Polling provides immediate feedback.

### Recommended: Hybrid
- **Primary**: Webhook updates order status server-side.
- **Secondary**: Frontend polls to reflect status to user immediately.

---

## 5. Idempotency Key Usage

| Flow | Usage |
|------|-------|
| **Checkout Pro** (current) | UUID4 stored in `Pago.idempotency_key` but **never sent to MP** — preferences are idempotent by design |
| **Checkout API** (target) | UUID4 stored in `Pago.idempotency_key` **AND sent to MP** as `x-idempotency-key` header via `RequestOptions.custom_headers` |

This is the only code change needed for the backend — passing the already-generated key to MP.

---

## 6. Integration Gaps vs Current Backend

| Gap | Current State | Required |
|-----|--------------|----------|
| MP SDK | ✅ Installed (`mercadopago` package) | Already available |
| Access Token | ✅ Configured in env | Already available |
| Preference creation | ✅ Implemented (Checkout Pro) | **Switch to `sdk.payment().create()`** |
| Webhook handler | ✅ Complete (3 formats) | No changes needed |
| Idempotency | ✅ UUID4 per Pago row | Pass to MP via `RequestOptions` |
| Payment status sync | ✅ Via webhook + FSM | No changes needed |
| Card tokenization | ❌ Not implemented | Frontend: MP.js Secure Fields |
| Payment method selection | ❌ Not implemented | Frontend: card form + method picker |
| Frontend payment pages | ⚠️ Partial (PaymentPage exists) | Update for Checkout API flow |

---

## 7. Official Documentation Links

- [Checkout API Overview](https://www.mercadopago.com/developers/en/docs/checkout-api/introduction)
- [Create Payment (API Reference)](https://www.mercadopago.com/developers/en/reference/payments/_payments/post)
- [Webhook Notifications](https://www.mercadopago.com/developers/en/docs/checkout-api/integrations/webhooks)
- [Payment Status Reference](https://www.mercadopago.com/developers/en/docs/checkout-api/integrations/payment-status)
- [API Reference](https://www.mercadopago.com/developers/en/reference)
- [Python SDK](https://github.com/mercadopago/sdk-python) (v2.4.0, Apr 2026)
- [MP.js Secure Fields](https://www.mercadopago.com/developers/en/docs/checkout-api/integrations/secure-fields)

---

## 8. Recommended Implementation Order

1. **Backend**: Switch `sdk.preference().create()` → `sdk.payment().create()`
2. **Backend**: Accept `card_token` + `payment_method_id` in `POST /pagos/`
3. **Backend**: Pass `x-idempotency-key` via `RequestOptions.custom_headers`
4. **Backend**: Handle synchronous response — update Pago + order immediately
5. **Frontend**: MP.js Secure Fields integration (card form, tokenization)
6. **Frontend**: Update PaymentPage for Checkout API flow
7. **Frontend**: Handle ticket methods (`external_resource_url`)
8. **Testing**: Sandbox end-to-end flow with test cards
