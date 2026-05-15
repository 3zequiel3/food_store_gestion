import { useState } from 'react';
import { SecureCardForm } from './SecureCardForm';
import { createInlinePayment } from '../services/payments.service';
import type { PaymentResponse } from '../types/payments.types';

interface PaymentFormProps {
  pedidoId: number;
  onSuccess: (response: PaymentResponse) => void;
  onError: (message: string) => void;
}

export function PaymentForm({ pedidoId, onSuccess, onError }: PaymentFormProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  async function handlePaymentSubmit(token: string, paymentMethodId: string) {
    setIsProcessing(true);
    try {
      const response = await createInlinePayment({
        pedido_id: pedidoId,
        card_token: token,
        payment_method_id: paymentMethodId,
        installments: 1,
        idempotency_key: crypto.randomUUID(),
      });

      if (response.mp_status === 'approved') {
        onSuccess(response);
      } else if (response.mp_status === 'rejected' || response.mp_status === 'cancelled') {
        const detail = response.status_detail ?? 'Pago rechazado. Intentá con otra tarjeta.';
        onError(detail);
      } else {
        onError(`Estado de pago inesperado: ${response.mp_status}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al procesar el pago.';
      onError(message);
    } finally {
      setIsProcessing(false);
    }
  }

  function handleCardError(message: string) {
    onError(message);
  }

  return (
    <SecureCardForm
      onSubmit={handlePaymentSubmit}
      onError={handleCardError}
      isLoading={isProcessing}
    />
  );
}
