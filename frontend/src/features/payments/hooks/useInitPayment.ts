import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createInlinePayment } from '../services/payments.service';
import type { PaymentResponse } from '../types/payments.types';
import { ApiError } from '../../../api/interceptors/error';

interface InlinePaymentInput {
  pedidoId: number;
  cardToken: string;
  paymentMethodId: string;
  installments?: number;
}

export function useInitPayment() {
  return useMutation<PaymentResponse, unknown, InlinePaymentInput>({
    mutationFn: async ({ pedidoId, cardToken, paymentMethodId, installments = 1 }) => {
      const data = await createInlinePayment({
        pedido_id: pedidoId,
        card_token: cardToken,
        payment_method_id: paymentMethodId,
        installments,
        idempotency_key: crypto.randomUUID(),
      });
      return data;
    },
    onError(error) {
      if (error instanceof ApiError) {
        toast.error('Error al procesar el pago', {
          description: error.detail || 'Intentá de nuevo.',
        });
      } else {
        toast.error('Error al procesar el pago', {
          description: error instanceof Error ? error.message : 'Intentá de nuevo.',
        });
      }
    },
  });
}
