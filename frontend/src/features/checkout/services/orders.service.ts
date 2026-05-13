import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { CrearPedidoRequest, PedidoRead } from '../types/checkout.types';

/**
 * Servicio de pedidos.
 *
 * createOrder envía el payload al backend para crear un nuevo pedido.
 */

/** POST /pedidos/ — crea un nuevo pedido y retorna PedidoRead */
export async function createOrder(payload: CrearPedidoRequest): Promise<PedidoRead> {
  const response = await apiClient.post<PedidoRead>(ENDPOINTS.pedidos.create, payload);
  return response.data;
}
