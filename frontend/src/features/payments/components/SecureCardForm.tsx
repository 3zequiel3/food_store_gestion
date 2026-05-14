import { useEffect, useRef, useState, useCallback } from 'react';
import { initMercadoPago, CardForm } from '@mercadopago/sdk-js';
import { Loader2, CreditCard } from 'lucide-react';

interface SecureCardFormProps {
  onSubmit: (token: string, paymentMethodId: string) => void;
  onError: (message: string) => void;
  isLoading?: boolean;
}

export function SecureCardForm({ onSubmit, onError, isLoading }: SecureCardFormProps) {
  const formRef = useRef<HTMLDivElement>(null);
  const cardFormRef = useRef<CardForm | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!cardFormRef.current || isLoading) return;
      cardFormRef.current.submit();
    },
    [isLoading],
  );

  useEffect(() => {
    const publicKey = import.meta.env.VITE_MP_PUBLIC_KEY;
    if (!publicKey) {
      setInitError('Falta la clave pública de MercadoPago.');
      return;
    }

    try {
      initMercadoPago(publicKey, { locale: 'es-AR' });
    } catch (err) {
      setInitError('Error al inicializar MercadoPago SDK.');
      return;
    }

    if (!formRef.current) return;

    const cardFormInstance = new CardForm(formRef.current, {
      onReady: () => {
        setIsReady(true);
      },
      onSubmit: (response: { token: string; paymentMethodId: string }) => {
        onSubmit(response.token, response.paymentMethodId);
      },
      onError: (error: { message?: string }) => {
        onError(error.message ?? 'Error al procesar la tarjeta.');
      },
    });

    cardFormRef.current = cardFormInstance;

    return () => {
      cardFormInstance.unmount();
      cardFormRef.current = null;
    };
  }, [onSubmit, onError]);

  if (initError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {initError}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div
        ref={formRef}
        className="min-h-[180px] rounded-lg border border-border bg-card p-4"
      >
        {!isReady && (
          <div className="flex items-center justify-center h-full py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Cargando formulario seguro…
            </span>
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={!isReady || isLoading}
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
