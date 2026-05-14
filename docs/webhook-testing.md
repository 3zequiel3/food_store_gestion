# Webhook Testing Guide — MercadoPago

## Prerequisites

- **ngrok installed**: `brew install ngrok` (macOS) or download from [ngrok.com](https://ngrok.com)
- **MercadoPago sandbox credentials**: Access token and public key from [MP Dashboard](https://www.mercadopago.com/developers/panel/app)
- **Backend running**: `uvicorn main:app --host 0.0.0.0 --port 8000` on localhost

## 1. Start the Tunnel

```bash
./scripts/dev-tunnel.sh
```

The script will:
1. Start ngrok forwarding to `localhost:8000`
2. Display the public URL
3. Show the full webhook endpoint URL

Copy the webhook URL (e.g. `https://abc123.ngrok-free.app/api/v1/pagos/webhook/mercadopago`).

## 2. Configure the Webhook in MP Dashboard

1. Go to [MercadoPago Dashboard](https://www.mercadopago.com/developers/panel/app)
2. Select your sandbox application
3. Navigate to **Webhooks** section
4. Add a new webhook:
   - **URL**: Paste the ngrok webhook URL from step 1
   - **Events**: Select `payment` (and `merchant_order` if applicable)
5. Save the configuration

## 3. Test the Webhook

### Trigger a Test Payment

1. Use the checkout flow in the app to create a payment
2. When redirected to MercadoPago, use a **sandbox test card**:

| Result | Card Number |
|--------|-------------|
| ✅ Approved | `5031 7557 3453 0604` |
| ❌ Rejected | `4000 0000 0000 0002` |

- **Name**: Any name (e.g. "Test User")
- **Expiry**: Any future date (e.g. `12/30`)
- **CVV**: `123`
- **Document**: `12345678`

### 4. Verify Webhook Delivery

Check the backend logs for incoming webhook requests:

```bash
# Look for webhook-related log entries
# The backend logs each webhook receipt with its format and processing result
```

Expected behavior:
- **Approved payment**: Order transitions to `paid` status
- **Rejected payment**: Order stays in `pending` or transitions to `failed`

## Webhook Formats Supported

The backend handles **3 webhook formats** from MercadoPago:

### Format 1: Modern Webhook (Preferred)

```json
{
  "type": "payment",
  "data": {
    "id": "123456789"
  }
}
```

Sent as `POST` with `Content-Type: application/json`.

### Format 2: Old IPN (Legacy)

```json
{
  "topic": "payment",
  "resource": "https://api.mercadopago.com/v1/payments/123456789"
}
```

Sent as `POST` with `Content-Type: application/json`. The backend fetches payment details from the `resource` URL.

### Format 3: Classic IPN via Query Params

```
POST /api/v1/pagos/webhook/mercadopago?topic=payment&id=123456789
```

Sent as `POST` with query parameters instead of a JSON body. The backend extracts `topic` and `id` from the URL.

## Railway Deployment Note

When deploying to Railway, the `release` phase in `Procfile` runs:

```
release: alembic upgrade head
```

This automatically applies any pending database migrations **before** the web service starts. This means:

- New payment-related tables/columns are created automatically on deploy
- If a migration fails, the deploy is rolled back (the web process won't start)
- No manual migration step is needed after pushing code

**Important**: When testing webhooks on a Railway-deployed instance (not local ngrok), configure the webhook URL to point to your Railway deployment URL instead of ngrok.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ngrok won't start | Check port 8000 isn't already in use (`lsof -i :8000`) |
| Webhook not received | Verify ngrok tunnel is active at `http://localhost:4040` |
| 403 on webhook endpoint | Check the backend is running and the route is registered |
| Payment not updating | Check backend logs for webhook processing errors |
