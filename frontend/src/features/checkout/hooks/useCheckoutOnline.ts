import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { createCheckoutOnline } from '../services/checkout.service';
import { useCartStore } from '../../cart/stores/cartStore';
import type {
  CheckoutOnlineRequest,
  CheckoutOnlineResponse,
  CheckoutErrorResponse,
} from '../types/checkout.types';
import { ApiError } from '../../../api/interceptors/error';

/**
 * Options for useCheckoutOnline hook.
 */
export interface UseCheckoutOnlineOptions {
  onSuccess?: (data: CheckoutOnlineResponse) => void;
}

/**
 * Hook for online checkout with MercadoPago payment.
 *
 * Wraps useMutation calling POST /api/v1/checkout/online.
 * On success: clears cart, navigates to confirmation page.
 * On error: shows toast with appropriate message based on status code.
 *
 * Strict mode: Only mp_status === 'approved' creates an order.
 * Other statuses (rejected, pending, in_process, cancelled) return 402
 * without creating an order.
 */
export function useCheckoutOnline(options?: UseCheckoutOnlineOptions) {
  const navigate = useNavigate();
  const cartItems = useCartStore((s) => s.items);
  const clearCart = useCartStore((s) => s.clearCart);

  return useMutation<CheckoutOnlineResponse, ApiError<CheckoutErrorResponse>, CheckoutOnlineRequest>({
    mutationFn: (payload) => createCheckoutOnline(payload),
    onSuccess(data) {
      // Capture items BEFORE clearing cart
      const snapshot = [...cartItems];
      clearCart();
      navigate(`/cliente/pedidos/${data.pedido_id}/confirmacion`, {
        state: { pedido: data, cartItems: snapshot, paymentStatus: data.mp_status },
      });
      options?.onSuccess?.(data);
    },
    onError(error) {
      // RFC 7807 error handling (D7)
      if (error instanceof ApiError) {
        const status = error.status;
        const detail = error.detail;
        const mpStatus = (error.data as CheckoutErrorResponse | undefined)?.mp_status;

        // 402 Payment Required — MP rejected/pending/cancelled
        if (status === 402) {
          if (mpStatus === 'rejected') {
            toast.error('Pago rechazado', {
              description: detail || 'Tu tarjeta fue rechazada. Probá con otra.',
            });
            return;
          }
          if (mpStatus === 'pending' || mpStatus === 'in_process') {
            toast.error('Pago en revisión', {
              description:
                'Tu pago quedó en revisión y no podemos confirmar el pedido. ' +
                'Probá con otra tarjeta o elegí pago en efectivo al retirar.',
            });
            return;
          }
          if (mpStatus === 'cancelled') {
            toast.error('Pago cancelado', {
              description: 'El pago fue cancelado. Probá con otro método.',
            });
            return;
          }
          // Generic 402
          toast.error('Error en el pago', {
            description: detail || 'No se pudo procesar el pago. Intentá de nuevo.',
          });
          return;
        }

        // 422 Unprocessable Entity — validation error (stock, product unavailable, etc.)
        if (status === 422) {
          if (detail?.toLowerCase().includes('stock')) {
            toast.error('Producto sin stock suficiente', {
              description: 'Volvé al carrito para ajustar las cantidades.',
              action: {
                label: 'Ir al catálogo',
                onClick: () => navigate('/cliente/catalogo'),
              },
            });
            return;
          }
          if (detail?.toLowerCase().includes('producto')) {
            toast.error('Producto no disponible', {
              description: detail,
            });
            return;
          }
        }

        // 404 Not Found — product or address not found
        if (status === 404) {
          if (detail?.toLowerCase().includes('direccion') || detail?.toLowerCase().includes('dirección')) {
            toast.error('Dirección no encontrada', {
              description: 'Seleccioná otra dirección de entrega.',
            });
            return;
          }
        }

        // 403 Forbidden
        if (status === 403) {
          toast.error('No tenés permisos para realizar esta acción.');
          return;
        }

        // 502 Bad Gateway — MP unreachable
        if (status === 502) {
          toast.error('Error de conexión', {
            description:
              'MercadoPago no respondió. Verificá tu conexión e intentá de nuevo en un momento.',
          });
          return;
        }

        // Generic error
        toast.error('Error al procesar el pago', {
          description: detail || 'Intentá de nuevo.',
        });
      } else {
        // Non-API error
        toast.error('Error al procesar el pago', {
          description: 'Intentá de nuevo.',
        });
      }
    },
  });
}
