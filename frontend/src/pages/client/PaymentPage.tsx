import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CreditCard, Loader2, AlertCircle, ArrowLeft, CheckCircle } from 'lucide-react';
import { PaymentForm } from '../../features/payments/components/PaymentForm';
import { useOrderDetail } from '../../features/orders/hooks/useOrderDetail';
import type { PaymentResponse } from '../../features/payments/types/payments.types';

export function PaymentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pedidoId = id ? Number(id) : null;

  const { data: order, isLoading: orderLoading } = useOrderDetail(pedidoId);

  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [paymentSuccess, setPaymentSuccess] = useState<PaymentResponse | null>(null);

  if (!pedidoId) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center space-y-4">
        <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
        <h1 className="text-xl font-semibold text-foreground">Pedido no encontrado</h1>
        <button
          onClick={() => navigate('/cliente/pedidos')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Ver mis pedidos
        </button>
      </div>
    );
  }

  if (orderLoading) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center">
        <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-foreground mb-2">Cargando pedido...</h1>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center space-y-4">
        <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
        <h1 className="text-xl font-semibold text-foreground">No se pudo cargar el pedido</h1>
        <button
          onClick={() => navigate('/cliente/pedidos')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Ver mis pedidos
        </button>
      </div>
    );
  }

  if (paymentSuccess) {
    return (
      <div className="max-w-md mx-auto py-20 px-4 text-center space-y-4">
        <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
        <h1 className="text-xl font-semibold text-foreground">¡Pago exitoso!</h1>
        <p className="text-muted-foreground text-sm">
          Tu pago fue procesado correctamente.
        </p>
        <button
          onClick={() => navigate(`/cliente/pedidos/${pedidoId}/confirmacion`)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          Ver confirmación
        </button>
      </div>
    );
  }

  function handleSuccess(response: PaymentResponse) {
    setPaymentSuccess(response);
  }

  function handleError(message: string) {
    setPaymentError(message);
  }

  function handleRetry() {
    setPaymentError(null);
  }

  const monto = parseFloat(order.total);

  return (
    <div className="max-w-lg mx-auto py-8 px-4">
      <button
        onClick={() => navigate(`/cliente/pedidos/${pedidoId}/confirmacion`)}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver al pedido
      </button>

      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <CreditCard className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-lg font-semibold text-foreground">Pagar pedido</h1>
            <p className="text-sm text-muted-foreground">
              Pedido #{pedidoId} — Total: ${monto.toLocaleString('es-AR', { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {paymentError && (
          <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
            <p className="text-sm text-destructive">{paymentError}</p>
            <button
              onClick={handleRetry}
              className="mt-2 text-sm text-destructive underline hover:no-underline"
            >
              Intentar de nuevo
            </button>
          </div>
        )}

        <PaymentForm
          pedidoId={pedidoId}
          monto={monto}
          onSuccess={handleSuccess}
          onError={handleError}
        />
      </div>
    </div>
  );
}
