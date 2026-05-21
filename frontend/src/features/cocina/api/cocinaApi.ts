import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { CocinaPedidoResponse } from '../types/cocina.types';

/**
 * GET /api/v1/cocina/pedidos
 * Devuelve pedidos en CONFIRMADO + EN_PREPARACION ordenados por antigüedad.
 */
export async function getKitchenOrders(): Promise<CocinaPedidoResponse[]> {
  const response = await apiClient.get<CocinaPedidoResponse[]>(ENDPOINTS.cocina.pedidos);
  return response.data;
}

/**
 * POST /api/v1/pedidos/{id}/transicionar
 * Transiciona el pedido al estado destino (EN_PREPARACION o TERMINADO).
 */
export async function transitionKitchenOrder(
  orderId: number,
  estadoDestino: string,
): Promise<{ pedido_id: number; estado_anterior: string; estado_nuevo: string }> {
  const response = await apiClient.post(ENDPOINTS.cocina.transicionar(orderId), {
    estado_codigo_destino: estadoDestino,
  });
  return response.data;
}
