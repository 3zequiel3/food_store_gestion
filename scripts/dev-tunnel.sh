#!/usr/bin/env bash
set -e

echo "🔌 Starting ngrok tunnel to localhost:8000..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo "   Install: brew install ngrok  (macOS) or download from https://ngrok.com"
    exit 1
fi

# Start ngrok in background
ngrok http 8000 --log=stdout &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get the public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "⚠️  Could not detect ngrok URL. Check http://localhost:4040"
else
    echo ""
    echo "✅ ngrok tunnel started!"
    echo "📡 Public URL: ${NGROK_URL}"
    echo "🔗 Webhook URL: ${NGROK_URL}/api/v1/pagos/webhook/mercadopago"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Copy the webhook URL above"
    echo "   2. Go to MercadoPago Dashboard → Your Integration → Webhooks"
    echo "   3. Paste the URL and save"
    echo "   4. Trigger a test payment to verify webhook delivery"
    echo ""
    echo "   Press Ctrl+C to stop the tunnel"
fi

# Wait for ngrok process
wait $NGROK_PID
