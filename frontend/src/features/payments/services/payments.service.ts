import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { PagoCreate, PagoRead } from '../types/payments.types';

export async function initiatePayment(pedidoId: number): Promise<PagoRead> {
  const payload: PagoCreate = { pedido_id: pedidoId };
  const response = await apiClient.post<PagoRead>(ENDPOINTS.pagos.create, payload);
  return response.data;
}

export async function getPaymentByOrder(pedidoId: number): Promise<PagoRead> {
  const response = await apiClient.get<PagoRead>(ENDPOINTS.pagos.porPedido(pedidoId));
  return response.data;
}
