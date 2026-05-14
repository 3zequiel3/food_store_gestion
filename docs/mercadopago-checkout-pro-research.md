# MercadoPago Checkout Pro — Research Document

**Date**: 2026-05-14
**Status**: Research / Planning
**Target Integration**: Food Store Backend (FastAPI)

---

## 1. Preference Creation Flow

Checkout Pro works by creating a **Preference** on the MercadoPago server, which returns a `init_point` URL. The user is redirected to that URL to complete payment.

### Flow
1. Backend calls `POST /checkout/preferences` with items, payer info, back URLs, and notification URL.
2. MercadoPago returns a preference object with:
   - `id` — preference identifier
   - `init_point` — URL to redirect the buyer (production)
   - `sandbox_init_point` — URL for sandbox/testing
3. Frontend redirects user to `init_point`.
4. User completes payment on MercadoPago's hosted checkout.
5. MercadoPago redirects back to one of the configured `back_urls`.

### Key Fields in Preference Request
```json
{
  "items": [
    {
      "id": "producto-1",
      "title": "Hamburguesa Clásica",
      "unit_price": 1500.00,
      "quantity": 2,
      "currency_id": "ARS"
    }
  ],
  "payer": {
    "email": "buyer@email.com"
  },
  "back_urls": {
    "success": "https://foodstore.com/pago/success",
    "failure": "https://foodstore.com/pago/failure",
    "pending": "https://foodstore.com/pago/pending"
  },
  "notification_url": "https://foodstore.com/api/v1/pagos/webhook/mercadopago",
  "auto_return": "approved"
}
```

### Integration Gap
Current backend has `POST /pagos/` endpoint but does **not** yet create MP preferences. The endpoint stores payment records but doesn't initiate the external checkout flow.

---

## 2. Webhook IPN (Instant Payment Notification) Format

MercadoPago sends POST requests to the `notification_url` when payment status changes.

### IPN Payload Structure
```
GET /webhook?data.id=1234567890&type=payment
```

The notification is a **query parameter** with `data.id` (payment ID) and `type`. The actual payment details must be fetched separately via:
```
GET /v1/payments/{data.id}
```

### Payment Statuses
| Status | Meaning | Action |
|--------|---------|--------|
| `approved` | Payment confirmed | Mark order as paid, start fulfillment |
| `pending` | Awaiting payment (e.g., Rapipago) | Wait, show pending UI |
| `in_process` | Payment being processed | Wait for final status |
| `rejected` | Payment declined | Notify user, allow retry |
| `cancelled` | User cancelled | Return to cart |
| `refunded` | Payment refunded | Process refund logic |
| `charged_back` | Chargeback | Flag for review |

### Integration Gap
Backend has `POST /pagos/webhook/mercadopago` endpoint but needs to:
1. Parse `data.id` from query params
2. Fetch full payment details from MP API
3. Update local payment/order status
4. Handle idempotency (duplicate notifications)

---

## 3. Return URL Behavior

After payment, MercadoPago redirects the user to one of the `back_urls` based on outcome:

- **Success URL**: User approved payment. Includes `collection_id`, `collection_status`, `payment_id`, `status` as query params.
- **Failure URL**: Payment was rejected.
- **Pending URL**: Payment is pending (cash payment methods).

### Important Notes
- `auto_return: "approved"` auto-redirects only for approved payments. For pending/rejected, user must click a button on MP's page.
- Return URL params are **not** a reliable source of truth — always verify via webhook or API call.
- The `collection_status` param on return URL may differ from actual payment status (race condition).

### Integration Gap
Frontend has no payment success/failure/pending pages. Need to create:
- `/cliente/pago/success?payment_id=...`
- `/cliente/pago/failure`
- `/cliente/pago/pending`

---

## 4. Notification Polling Strategy

As a fallback or complement to webhooks, the frontend can poll for payment status:

### Approach
1. After redirecting to MP checkout, store `preference_id` locally.
2. When user returns to success URL, poll `GET /pagos/pedido/{pedidoId}` every 2-3 seconds.
3. Stop polling when status is `approved`, `rejected`, or `cancelled`.
4. Max polling attempts: ~30 (60-90 seconds), then show "contact support" message.

### Why Polling?
- Webhooks may be delayed or lost (network issues).
- User may close browser before webhook arrives.
- Polling provides immediate feedback on return.

### Recommended: Hybrid
- **Primary**: Webhook updates order status server-side.
- **Secondary**: Frontend polls to reflect status to user immediately.

---

## 5. Integration Gaps vs Current Backend

| Gap | Current State | Required |
|-----|--------------|----------|
| MP SDK / API client | Not installed | `mercadopago` Python package or direct HTTP calls |
| Preference creation | Not implemented | `POST /checkout/preferences` on payment initiation |
| Webhook handler | Endpoint exists, logic incomplete | Parse IPN, fetch payment, update order |
| Access Token management | Not present | Store MP access token (env var), handle refresh |
| Payment status sync | No sync with MP | Poll or webhook to confirm payment |
| Frontend payment pages | Not created | Success/failure/pending pages |
| Order → Payment linkage | Order exists, payment record created | Link preference_id to order for tracking |

---

## 6. Official Documentation Links

- [Checkout Pro Overview](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/introduction)
- [Create Preference](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/checkout-creation/create-preference)
- [Webhook Notifications](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/integrations/webhooks)
- [Payment Status Reference](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/integrations/payment-status)
- [API Reference](https://www.mercadopago.com.ar/developers/es/reference)
- [Python SDK](https://github.com/mercadopago/sdk-python)

---

## 7. Recommended Implementation Order

1. **Backend**: Install MP SDK, add access token config
2. **Backend**: Implement preference creation in `POST /pagos/`
3. **Backend**: Complete webhook handler at `POST /pagos/webhook/mercadopago`
4. **Frontend**: Add payment initiation flow (redirect to `init_point`)
5. **Frontend**: Create success/failure/pending pages
6. **Frontend**: Add polling fallback for payment status
7. **Testing**: Sandbox end-to-end flow with test cards
