import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, ShoppingBag, CreditCard, ArrowLeft, Package } from 'lucide-react';
import type { PedidoRead } from '../../checkout/types/checkout.types';
import type { CartItem } from '../../cart/types/cart.types';

interface LocationState {
  pedido?: PedidoRead;
  cartItems?: CartItem[];
}

/**
 * Página de confirmación post-creación de pedido.
 *
 * Lee el pedido creado y los items del carrito del location state
 * (pasados por useCreateOrder antes de clearCart).
 * Si no hay state (ej: refresh), muestra un fallback genérico.
 *
 * Muestra:
 * - Número de pedido
 * - Estado (PENDIENTE)
 * - Resumen de items (desde location state, NO cartStore)
 * - Total (desde PedidoRead.total)
 * - Botones "Ir a pagar" y "Ver mis pedidos"
 */
export function OrderConfirmationPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as LocationState | null;
  const pedido = state?.pedido;
  const cartItems = state?.cartItems ?? [];

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

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header con éxito */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center h-16 w-16 rounded-full bg-success/10 mb-4">
          <CheckCircle className="h-8 w-8 text-success" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">¡Pedido confirmado!</h1>
        <p className="text-muted-foreground">
          Pedido <span className="font-semibold text-foreground">#{pedido.id}</span>
        </p>
      </div>

      {/* Estado del pedido */}
      <div className="bg-card border border-border rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Estado</p>
            <p className="font-semibold text-foreground">
              PENDIENTE — Esperando pago
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold text-foreground">
              ${Number(pedido.total).toFixed(2)}
            </p>
          </div>
        </div>
      </div>

      {/* Resumen de items (si están disponibles en el cartStore) */}
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
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => navigate('/cliente/pedidos')}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-semibold"
        >
          <Package className="h-4 w-4" />
          Ver mis pedidos
        </button>
        <button
          onClick={() => navigate(`/cliente/pedidos/${pedido.id}/pago`)}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 border border-border bg-card text-foreground rounded-lg hover:bg-accent transition-colors font-semibold"
        >
          <CreditCard className="h-4 w-4" />
          Ir a pagar
        </button>
      </div>

      {/* Link para seguir comprando */}
      <button
        onClick={() => navigate('/cliente/catalogo')}
        className="w-full mt-4 inline-flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Seguir comprando
      </button>
    </div>
  );
}
