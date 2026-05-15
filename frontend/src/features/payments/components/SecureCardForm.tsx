import { useEffect, useState, useCallback } from 'react';
import { loadMercadoPago } from '@mercadopago/sdk-js';
import { Loader2, CreditCard } from 'lucide-react';

interface SecureCardFormProps {
  onSubmit: (token: string, paymentMethodId: string) => void;
  onError: (message: string) => void;
  isLoading?: boolean;
}

type MercadoPagoInstance = {
  createCardToken: (cardData: {
    cardNumber: string;
    cardholderName: string;
    cardExpirationMonth: string;
    cardExpirationYear: string;
    securityCode: string;
    identificationType?: string;
    identificationNumber?: string;
  }) => Promise<{ id: string; payment_method_id: string }>;
  getPaymentMethods: (params: { bin: string }) => Promise<{ results: Array<{ id: string }> }>;
  getIdentificationTypes: () => Promise<Array<{ id: string; name: string }>>;
};

// loadMercadoPago() injects <script src="sdk.mercadopago.com/js/v2">
// and resolves the MercadoPago constructor. The SDK has no TS types,
// so we type the result via a cast.
async function loadMP(publicKey: string): Promise<MercadoPagoInstance> {
  const sdk = await loadMercadoPago();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const MercadoPago = sdk as any;
  const mp = new MercadoPago(publicKey, { locale: 'es-AR', trackingDisabled: true });
  
  return mp as MercadoPagoInstance;
}

export function SecureCardForm({ onSubmit, onError, isLoading }: SecureCardFormProps) {
  const [mpInstance, setMpInstance] = useState<MercadoPagoInstance | null>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  // Form state
  const [cardNumber, setCardNumber] = useState('');
  const [expMonth, setExpMonth] = useState('');
  const [expYear, setExpYear] = useState('');
  const [cvv, setCvv] = useState('');
  const [cardholderName, setCardholderName] = useState('');

  // Initialize MP SDK via loadMercadoPago loader
  useEffect(() => {
    const publicKey = import.meta.env.VITE_MP_PUBLIC_KEY;
    if (!publicKey) return;

    let cancelled = false;

    loadMP(publicKey)
      .then((mp) => {
        if (cancelled || !mp) return;
        console.log('[SecureCardForm] MP SDK initialized with public key:', publicKey.slice(0, 12) + '...');
        setMpInstance(mp);
        setSdkReady(true);
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('[SecureCardForm] Failed to load MP SDK:', err);
          setInitError('Error al cargar MercadoPago SDK. Recargá la página.');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Early return for missing public key — computed during render, not in effect
  const publicKey = import.meta.env.VITE_MP_PUBLIC_KEY;
  if (!publicKey) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        Falta la clave pública de MercadoPago (VITE_MP_PUBLIC_KEY).
      </div>
    );
  }

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!mpInstance || isLoading) return;

      if (!cardNumber.trim() || !expMonth.trim() || !expYear.trim() || !cvv.trim() || !cardholderName.trim()) {
        onError('Completá todos los campos de la tarjeta.');
        return;
      }

      try {
        const { id: token, payment_method_id: paymentMethodId } =
          await mpInstance.createCardToken({
            cardNumber: cardNumber.replace(/\s/g, ''),
            cardholderName: cardholderName,
            cardExpirationMonth: expMonth,
            cardExpirationYear: expYear,
            securityCode: cvv,
          });

        console.log('[SecureCardForm] Token generated successfully:', { token: token.slice(0, 8) + '...', paymentMethodId });
        onSubmit(token, paymentMethodId);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        console.error('[SecureCardForm] Card tokenization failed:', err);
        onError(`Error al tokenizar la tarjeta: ${message}`);
      }
    },
    [mpInstance, isLoading, cardNumber, expMonth, expYear, cvv, cardholderName, onSubmit, onError],
  );

  if (initError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {initError}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        {!sdkReady && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Cargando formulario de pago…
            </span>
          </div>
        )}

        {sdkReady && (
          <>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Número de tarjeta
              </label>
              <input
                type="text"
                inputMode="numeric"
                placeholder="4111 1111 1111 1111"
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value.replace(/\D/g, '').slice(0, 16))}
                maxLength={16}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isLoading}
                autoComplete="cc-number"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Vencimiento
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="MM"
                    value={expMonth}
                    onChange={(e) => setExpMonth(e.target.value.replace(/\D/g, '').slice(0, 2))}
                    maxLength={2}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={isLoading}
                  />
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="YY"
                    value={expYear}
                    onChange={(e) => setExpYear(e.target.value.replace(/\D/g, '').slice(0, 2))}
                    maxLength={2}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={isLoading}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  CVV
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="123"
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  maxLength={4}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={isLoading}
                  autoComplete="cc-csc"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Nombre del titular
              </label>
              <input
                type="text"
                placeholder="Como aparece en la tarjeta"
                value={cardholderName}
                onChange={(e) => setCardholderName(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isLoading}
                autoComplete="cc-name"
              />
            </div>
          </>
        )}
      </div>

      <button
        type="submit"
        disabled={!sdkReady || isLoading}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Procesando pago…
          </>
        ) : (
          <>
            <CreditCard className="h-4 w-4" />
            Pagar ahora
          </>
        )}
      </button>
    </form>
  );
}
