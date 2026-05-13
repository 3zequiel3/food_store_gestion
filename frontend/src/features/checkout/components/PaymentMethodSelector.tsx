import { CreditCard, Loader2 } from 'lucide-react';
import { usePaymentMethods } from '../hooks/usePaymentMethods';
import type { PaymentMethodRead } from '../types/checkout.types';

interface PaymentMethodSelectorProps {
  selectedPaymentMethod: string | null;
  onSelect: (codigo: string) => void;
}

export function PaymentMethodSelector({
  selectedPaymentMethod,
  onSelect,
}: PaymentMethodSelectorProps) {
  const { data: paymentMethods, isLoading } = usePaymentMethods();

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="font-semibold text-foreground">Forma de pago</h3>
        <div className="flex items-center gap-2 p-4 rounded-lg bg-glass backdrop-blur-sm border border-glass-border">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Cargando formas de pago...</span>
        </div>
      </div>
    );
  }

  if (!paymentMethods || paymentMethods.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="font-semibold text-foreground">Forma de pago</h3>
        <p className="text-sm text-muted-foreground">
          No hay formas de pago disponibles en este momento.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-foreground">Forma de pago</h3>

      <div className="space-y-2">
        {paymentMethods.map((method: PaymentMethodRead) => (
          <label
            key={method.codigo}
            className={`
              flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-150
              ${selectedPaymentMethod === method.codigo
                ? 'border-primary bg-primary/10 shadow-sm shadow-primary/10'
                : 'border-glass-border bg-glass backdrop-blur-sm hover:bg-glass-hover'
              }
            `}
          >
            <input
              type="radio"
              name="paymentMethod"
              value={method.codigo}
              checked={selectedPaymentMethod === method.codigo}
              onChange={() => onSelect(method.codigo)}
              className="sr-only"
            />
            <div className={`
              h-5 w-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              ${selectedPaymentMethod === method.codigo ? 'border-primary' : 'border-muted-foreground'}
            `}>
              {selectedPaymentMethod === method.codigo && (
                <div className="h-2.5 w-2.5 rounded-full bg-primary" />
              )}
            </div>
            <div className="flex items-center gap-3 flex-1">
              <CreditCard className="h-5 w-5 text-muted-foreground" />
              <div className="flex-1">
                <p className="font-medium text-foreground">{method.descripcion}</p>
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
