import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, ShoppingBag, Package, CreditCard, Truck } from 'lucide-react';
import type {
  CheckoutOnlineResponse,
  CheckoutPickupEfectivoResponse,
} from '../../checkout/types/checkout.types';
import type { CartItem } from '../../cart/types/cart.types';

interface LocationState {
  pedido?: CheckoutOnlineResponse | CheckoutPickupEfectivoResponse;
  cartItems?: CartItem[];
  paymentStatus?: string; // 'approved' for online, undefined for efectivo
  paymentMethod?: 'efectivo'; // For pickup+efectivo
}

/**
 * OrderConfirmationPage — post-checkout confirmation.
 *
 * Updated for checkout-pay-first-flow change:
 * - Online payment: shows mp_status, no "Ir a pagar" button (already paid)
 * - Pickup+efectivo: shows "Pagás al retirar" message
 * - PENDIENTE semántica: "esperando que el local acepte" (D4)
 */
export function OrderConfirmationPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as LocationState | null;
  const pedido = state?.pedido;
  const cartItems = state?.cartItems ?? [];
  const paymentStatus = state?.paymentStatus;
  const paymentMethod = state?.paymentMethod;

  // Determine payment type
  const isOnlinePayment = 'mp_status' in (pedido || {});
  const isPickupEfectivo = paymentMethod === 'efectivo';

  // Fallback si no hay location state (ej: refresh)
  if (!pedido) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="text-center space-y-4">
          <CheckCircle className="h-16 w-16 text-success mx-auto" />
          <h1 className="text-2xl font-bold text-foreground">Pedido creado</h1>
          <p className="text-muted-foreground">
            Tu pedido #{id} fue creado exitosamente.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => navigate('/cliente/catalogo')}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <ShoppingBag className="h-4 w-4" />
              Seguir comprando
            </button>
            <button
              onClick={() => navigate('/cliente/pedidos')}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 border border-border bg-card text-foreground rounded-lg hover:bg-accent transition-colors"
            >
              <Package className="h-4 w-4" />
              Ver mis pedidos
            </button>
          </div>
        </div>
      </div>
    );
  }

  const hasItems = cartItems.length > 0;

  // Status message based on payment type
  const getStatusMessage = () => {
    if (isOnlinePayment && paymentStatus === 'approved') {
      return {
        title: '¡Pago confirmado!',
        subtitle: 'Tu pedido está siendo procesado',
        description:
          'PENDIENTE — Esperando que el local acepte tu pedido',
        icon: CheckCircle,
        iconColor: 'text-success',
      };
    }
    if (isPickupEfectivo) {
      return {
        title: '¡Pedido confirmado!',
        subtitle: 'Retiro en local — Pagás al retirar',
        description:
          'PENDIENTE — Esperando que el local acepte tu pedido',
        icon: Package,
        iconColor: 'text-primary',
      };
    }
    // Fallback
    return {
      title: '¡Pedido confirmado!',
      subtitle: 'Tu pedido está siendo procesado',
      description: 'PENDIENTE — Esperando que el local acepte tu pedido',
      icon: CheckCircle,
      iconColor: 'text-success',
    };
  };

  const statusInfo = getStatusMessage();
  const StatusIcon = statusInfo.icon;

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header con éxito */}
      <div className="text-center mb-8">
        <div className={`inline-flex items-center justify-center h-16 w-16 rounded-full bg-${statusInfo.iconColor}/10 mb-4`}>
          <StatusIcon className={`h-8 w-8 ${statusInfo.iconColor}`} />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">
          {statusInfo.title}
        </h1>
        <p className="text-muted-foreground mb-1">
          {statusInfo.subtitle}
        </p>
        <p className="text-sm text-muted-foreground">
          Pedido <span className="font-semibold text-foreground">#{'pedido_id' in pedido ? pedido.pedido_id : id}</span>
        </p>
      </div>

      {/* Estado del pedido y total */}
      <div className="bg-card border border-border rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Estado</p>
            <p className="font-semibold text-foreground mt-1">
              {statusInfo.description}
            </p>
            {isPickupEfectivo && (
              <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                <Truck className="h-3 w-3" />
                Retirás en el local
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold text-foreground">
              ${isOnlinePayment ? 'Pagado' : 'Pendiente'}
            </p>
          </div>
        </div>
      </div>

      {/* Payment details for online payment */}
      {isOnlinePayment && (
        <div className="bg-card border border-border rounded-lg p-4 mb-6">
          <div className="flex items-center gap-3">
            <CreditCard className="h-5 w-5 text-success" />
            <div>
              <p className="text-sm font-medium text-foreground">Pago aprobado</p>
              <p className="text-xs text-muted-foreground">
                Tu pago fue procesado exitosamente
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Resumen de items (si están disponibles) */}
      {hasItems && (
        <div className="bg-card border border-border rounded-lg p-4 mb-6">
          <h2 className="font-semibold text-foreground mb-3">Resumen de tu pedido</h2>
          <ul className="space-y-2">
            {cartItems.map((item) => (
              <li key={item.producto_id} className="flex justify-between text-sm">
                <span className="text-foreground">
                  {item.nombre} x {item.cantidad}
                </span>
                <span className="text-muted-foreground">
                  ${(Number(item.precio) * item.cantidad).toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Botones de acción */}
      <div className="flex flex-col gap-3">
        <button
          onClick={() => navigate('/cliente/pedidos')}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-semibold"
        >
          <Package className="h-4 w-4" />
          Ver mis pedidos
        </button>
        <button
          onClick={() => navigate('/cliente/catalogo')}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 border border-border bg-card text-foreground rounded-lg hover:bg-accent transition-colors font-semibold"
        >
          <ShoppingBag className="h-4 w-4" />
          Seguir comprando
        </button>
      </div>

      {/* Info adicional */}
      <div className="mt-6 p-4 bg-muted/50 rounded-lg">
        <p className="text-xs text-muted-foreground text-center">
          {isPickupEfectivo
            ? 'Te avisaremos cuando tu pedido esté listo para retirar'
            : 'Te avisaremos cuando el local confirme tu pedido'}
        </p>
      </div>
    </div>
  );
}
