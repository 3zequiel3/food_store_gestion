import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  PaginatedPedidos,
  PedidoDetalle,
  OrderFilters,
  AvanzarEstadoRequest,
  EstadoCodigo,
  TransicionarRequest,
  TransicionarResponse,
} from '../types/orders.types';

export async function listOrders(filters: OrderFilters = {}): Promise<PaginatedPedidos> {
  const params: Record<string, string | number> = {};
  if (filters.estado) params.estado = filters.estado;
  if (filters.desde) params.desde = filters.desde;
  if (filters.hasta) params.hasta = filters.hasta;
  if (filters.q) params.q = filters.q;
  if (filters.page) params.page = filters.page;
  if (filters.limit) params.limit = filters.limit;

  const response = await apiClient.get<PaginatedPedidos>(ENDPOINTS.pedidos.list, { params });
  return response.data;
}

export async function getOrderDetail(id: number): Promise<PedidoDetalle> {
  const response = await apiClient.get<PedidoDetalle>(ENDPOINTS.pedidos.detail(id));
  return response.data;
}

export async function advanceOrderState(
  id: number,
  nuevo_estado: EstadoCodigo,
  motivo?: string,
): Promise<PedidoDetalle> {
  const body: AvanzarEstadoRequest = { nuevo_estado };
  if (motivo) body.motivo = motivo;
  const response = await apiClient.patch<PedidoDetalle>(ENDPOINTS.pedidos.estado(id), body);
  return response.data;
}

/** Transition order state via FSM (new endpoint). */
export async function transicionarEstado(
  pedidoId: number,
  estadoDestino: string,
  motivo?: string,
): Promise<TransicionarResponse> {
  const body: TransicionarRequest = { estado_codigo_destino: estadoDestino };
  if (motivo) body.motivo = motivo;
  const response = await apiClient.post<TransicionarResponse>(
    `/pedidos/${pedidoId}/transicionar`,
    body,
  );
  return response.data;
}
