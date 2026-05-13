import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CreditCard, Loader2, AlertCircle, ArrowLeft } from 'lucide-react';
import { useInitPayment } from '../../features/payments/hooks/useInitPayment';

export function PaymentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pedidoId = id ? Number(id) : null;
  const calledRef = useRef(false);

  const { mutate: initPayment, isPending, isError } = useInitPayment();

  useEffect(() => {
    if (pedidoId && !calledRef.current) {
      calledRef.current = true;
      initPayment(pedidoId);
    }
  }, [pedidoId, initPayment]);

  if (isPending) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center">
        <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-foreground mb-2">Iniciando pago...</h1>
        <p className="text-muted-foreground text-sm">Estamos conectando con MercadoPago.</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center space-y-4">
        <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
        <h1 className="text-xl font-semibold text-foreground">No se pudo iniciar el pago</h1>
        <p className="text-muted-foreground text-sm">
          Revisá el estado del pedido o intentá de nuevo.
        </p>
        <button
          onClick={() => navigate(`/cliente/pedidos/${id}/confirmacion`)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al pedido
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto py-20 px-4 text-center">
      <CreditCard className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <h1 className="text-xl font-semibold text-foreground mb-2">Redirigiendo a MercadoPago...</h1>
      <p className="text-muted-foreground text-sm mb-4">
        Si no fuiste redirigido automáticamente, volvé al pedido.
      </p>
      <button
        onClick={() => navigate(`/cliente/pedidos/${id}/confirmacion`)}
        className="text-sm text-muted-foreground hover:text-foreground underline inline-flex items-center gap-1"
      >
        <ArrowLeft className="h-3 w-3" />
        Volver al pedido
      </button>
    </div>
  );
}
