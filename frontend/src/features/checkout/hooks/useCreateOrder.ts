import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { createOrder } from '../services/orders.service';
import { useCartStore } from '../../cart/stores/cartStore';
import type { CrearPedidoRequest, PedidoRead } from '../types/checkout.types';
import { ApiError } from '../../../api/interceptors/error';

/**
 * Hook para crear un pedido.
 *
 * Wrappea useMutation que llama a POST /pedidos/.
 * En onSuccess: captura los items del carrito (antes de clearCart),
 * navega a la página de confirmación con items + pedido en location state.
 * En onError: muestra toast con el error según el tipo (D7).
 */

interface UseCreateOrderOptions {
  onSuccess?: (data: PedidoRead) => void;
}

export function useCreateOrder(options?: UseCreateOrderOptions) {
  const navigate = useNavigate();
  const cartItems = useCartStore((s) => s.items);
  const clearCart = useCartStore((s) => s.clearCart);

  return useMutation({
    mutationFn: (payload: CrearPedidoRequest) => createOrder(payload),
    onSuccess(data) {
      // Capturar items ANTES de limpiar el carrito
      const snapshot = [...cartItems];
      clearCart();
      navigate(`/cliente/pedidos/${data.id}/confirmacion`, {
        state: { pedido: data, cartItems: snapshot },
      });
      options?.onSuccess?.(data);
    },
    onError(error) {
      // Manejo de errores RFC 7807 (D7)
      if (error instanceof ApiError) {
        const status = error.status;
        const detail = error.detail || '';

        if (status === 422) {
          if (detail.toLowerCase().includes('stock')) {
            toast.error('Producto sin stock suficiente', {
              description: 'Volvé al carrito para ajustar las cantidades.',
              action: {
                label: 'Ir al catálogo',
                onClick: () => navigate('/cliente/catalogo'),
              },
            });
            return;
          }
          if (detail.toLowerCase().includes('pago') || detail.toLowerCase().includes('forma de pago')) {
            toast.error('Forma de pago no disponible', {
              description: 'Seleccioná otra forma de pago.',
            });
            return;
          }
        }

        if (status === 404) {
          if (detail.toLowerCase().includes('direccion') || detail.toLowerCase().includes('dirección')) {
            toast.error('Dirección no encontrada', {
              description: 'Seleccioná otra dirección de entrega.',
            });
            return;
          }
        }

        if (status === 403) {
          toast.error('No tenés permisos para crear pedidos.');
          return;
        }

        // Error genérico
        toast.error('Error al crear el pedido', {
          description: detail || 'Intentá de nuevo.',
        });
      } else {
        // Error no-API
        toast.error('Error al crear el pedido', {
          description: 'Intentá de nuevo.',
        });
      }
    },
  });
}
