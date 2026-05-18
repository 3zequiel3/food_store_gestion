import { useState } from 'react';
import { SecureCardForm } from './SecureCardForm';
import { createInlinePayment } from '../services/payments.service';
import { friendlyMessageFor } from '../lib/statusDetailMessages';
import type { PaymentResponse } from '../types/payments.types';

// Design decision D6: classify MP statuses into 4 semantic buckets.
const TERMINAL_SUCCESS = ['approved'] as const;
const PENDING_REVIEW = ['pending', 'in_process', 'authorized'] as const;
const TERMINAL_FAILURE = ['rejected', 'cancelled'] as const;

interface PaymentFormProps {
  pedidoId: number;
  onSuccess: (response: PaymentResponse) => void;
  /** Called when MP returns a pending/in_process/authorized status. */
  onPending: (response: PaymentResponse, message: string) => void;
  onError: (message: string) => void;
}

export function PaymentForm({ pedidoId, onSuccess, onPending, onError }: PaymentFormProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  async function handlePaymentSubmit(
    token: string,
    paymentMethodId: string,
    identificationType: string,
    identificationNumber: string,
  ) {
    setIsProcessing(true);
    try {
      const response = await createInlinePayment({
        pedido_id: pedidoId,
        card_token: token,
        payment_method_id: paymentMethodId,
        installments: 1,
        idempotency_key: crypto.randomUUID(),
        identification_type: identificationType,
        identification_number: identificationNumber,
      });

      const status = response.mp_status;

      if ((TERMINAL_SUCCESS as readonly string[]).includes(status)) {
        onSuccess(response);
      } else if ((PENDING_REVIEW as readonly string[]).includes(status)) {
        const message = friendlyMessageFor(response.status_detail);
        onPending(response, message);
      } else if ((TERMINAL_FAILURE as readonly string[]).includes(status)) {
        const message = friendlyMessageFor(response.status_detail);
        onError(message);
      } else {
        // Unexpected status (e.g. refunded, charged_back)
        onError(`Resultado inesperado: ${status}`);
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
