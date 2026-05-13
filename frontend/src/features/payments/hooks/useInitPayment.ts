import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { initiatePayment } from '../services/payments.service';
import { ApiError } from '../../../api/interceptors/error';

export function useInitPayment() {
  return useMutation({
    mutationFn: async (pedidoId: number) => {
      const data = await initiatePayment(pedidoId);
      if (!data.init_point) {
        throw new Error('No se recibió el link de pago de MercadoPago.');
      }
      return data;
    },
    onSuccess(data) {
      window.location.href = data.init_point!;
    },
    onError(error) {
      if (error instanceof ApiError) {
        toast.error('Error al iniciar el pago', {
          description: error.detail || 'Intentá de nuevo.',
        });
      } else {
        toast.error('Error al iniciar el pago', {
          description: error instanceof Error ? error.message : 'Intentá de nuevo.',
        });
      }
    },
  });
}
