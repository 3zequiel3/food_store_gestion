import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { PaymentMethodRead } from '../types/checkout.types';

/**
 * Servicio de formas de pago.
 *
 * getPaymentMethods retorna las formas de pago habilitadas.
 */

/** GET /formas-pago — retorna formas de pago habilitadas */
export async function getPaymentMethods(): Promise<PaymentMethodRead[]> {
  const response = await apiClient.get<PaymentMethodRead[]>(ENDPOINTS.paymentMethods.list);
  return response.data;
}
