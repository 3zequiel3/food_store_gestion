import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { createCheckoutDeliveryEfectivo } from '../services/checkout.service';
import { useCartStore } from '../../cart/stores/cartStore';
import type {
  CheckoutDeliveryEfectivoRequest,
  CheckoutDeliveryEfectivoResponse,
} from '../types/checkout.types';
import { ApiError } from '../../../api/interceptors/error';

/**
 * Options for useCheckoutDeliveryEfectivo hook.
 */
export interface UseCheckoutDeliveryEfectivoOptions {
  onSuccess?: (data: CheckoutDeliveryEfectivoResponse) => void;
}

/**
 * Hook for delivery+transferencia/efectivo checkout (no online payment).
 *
 * Wraps useMutation calling POST /api/v1/checkout/delivery-efectivo.
 * On success: clears cart, navigates to confirmation page.
 * On error: shows toast with appropriate message based on status code.
 */
export function useCheckoutDeliveryEfectivo(options?: UseCheckoutDeliveryEfectivoOptions) {
  const navigate = useNavigate();
  const cartItems = useCartStore((s) => s.items);
  const clearCart = useCartStore((s) => s.clearCart);

  return useMutation<
    CheckoutDeliveryEfectivoResponse,
    ApiError,
    CheckoutDeliveryEfectivoRequest
  >({
    mutationFn: (payload) => createCheckoutDeliveryEfectivo(payload),
    onSuccess(data) {
      // Capture items BEFORE clearing cart
      const snapshot = [...cartItems];
      clearCart();
      navigate(`/cliente/pedidos/${data.pedido_id}/confirmacion`, {
        state: { pedido: data, cartItems: snapshot, paymentMethod: 'transferencia' },
      });
      options?.onSuccess?.(data);
    },
    onError(error) {
      // RFC 7807 error handling
      if (error instanceof ApiError) {
        const status = error.status;
        const detail = error.detail;

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

        // 404 Not Found — address not found
        if (status === 404) {
          if (detail?.toLowerCase().includes('direccion') || detail?.toLowerCase().includes('dirección')) {
            toast.error('Dirección no encontrada', {
              description: 'Seleccioná otra dirección de entrega.',
            });
            return;
          }
          toast.error('Producto no encontrado', {
            description: detail || 'El producto ya no está disponible.',
          });
          return;
        }

        // 403 Forbidden
        if (status === 403) {
          toast.error('No tenés permisos para realizar esta acción.');
          return;
        }

        // Generic error
        toast.error('Error al crear el pedido', {
          description: detail || 'Intentá de nuevo.',
        });
      } else {
        // Non-API error
        toast.error('Error al crear el pedido', {
          description: 'Intentá de nuevo.',
        });
      }
    },
  });
}
