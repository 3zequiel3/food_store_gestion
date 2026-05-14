import { useEffect, useState, useCallback } from 'react';
import { loadMercadoPago } from '@mercadopago/sdk-js';
import { Loader2, CreditCard } from 'lucide-react';

interface SecureCardFormProps {
  onSubmit: (token: string, paymentMethodId: string) => void;
  onError: (message: string) => void;
  isLoading?: boolean;
}

// MercadoPago SDK v0.0.3 exports loadMercadoPago() which injects a
// <script src="sdk.mercadopago.com/js/v2"> and resolves the global
// MercadoPago constructor on window.
declare global {
  interface Window {
    MercadoPago: new (
      publicKey: string,
      options?: { locale?: string },
    ) => {
      cardToken: {
        createCardToken: (cardData: {
          cardNumber: string;
          expirationMonth: string;
          expirationYear: string;
          securityCode: string;
          cardholderName: string;
          cardholderIdentification?: { type: string; number: string };
        }) => Promise<{ id: string; payment_method_id: string }>;
      };
    };
  }
}

export function SecureCardForm({ onSubmit, onError, isLoading }: SecureCardFormProps) {
  const [mpInstance, setMpInstance] = useState<InstanceType<Window['MercadoPago']> | null>(null);
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
    if (!publicKey) {
      setInitError('Falta la clave pública de MercadoPago (VITE_MP_PUBLIC_KEY).');
      return;
    }

    let cancelled = false;

    loadMercadoPago()
      .then((MercadoPago) => {
        if (cancelled || !MercadoPago) return;
        const mp = new MercadoPago(publicKey, { locale: 'es-AR' });
        setMpInstance(mp);
        setSdkReady(true);
      })
      .catch(() => {
        if (!cancelled) setInitError('Error al cargar MercadoPago SDK. Recargá la página.');
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
          await mpInstance.cardToken.createCardToken({
            cardNumber: cardNumber.replace(/\s/g, ''),
            expirationMonth: expMonth,
            expirationYear: expYear,
            securityCode: cvv,
            cardholderName: cardholderName,
          });

        onSubmit(token, paymentMethodId);
      } catch {
        onError('Error al tokenizar la tarjeta. Verificá los datos e intentá de nuevo.');
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
