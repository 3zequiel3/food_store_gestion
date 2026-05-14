import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  PagoCreate,
  PagoRead,
  PaymentCreateRequest,
  PaymentResponse,
} from '../types/payments.types';

export async function initiatePayment(pedidoId: number): Promise<PagoRead> {
  const payload: PagoCreate = { pedido_id: pedidoId };
  const response = await apiClient.post<PagoRead>(ENDPOINTS.pagos.create, payload);
  return response.data;
}

export async function getPaymentByOrder(pedidoId: number): Promise<PagoRead> {
  const response = await apiClient.get<PagoRead>(ENDPOINTS.pagos.porPedido(pedidoId));
  return response.data;
}

/** Inline payment via Secure Fields (no redirect). */
export async function createInlinePayment(
  data: PaymentCreateRequest,
): Promise<PaymentResponse> {
  const response = await apiClient.post<PaymentResponse>('/pagos', data);
  return response.data;
}

/** Get inline payment status for an order. */
export async function getInlinePaymentStatus(
  pedidoId: number,
): Promise<PaymentResponse> {
  const response = await apiClient.get<PaymentResponse>(
    `/pagos/pedido/${pedidoId}`,
  );
  return response.data;
}
