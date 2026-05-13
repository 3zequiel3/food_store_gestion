import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  Granularidad,
  MetricsDateFilter,
  PedidosPorEstadoResponse,
  ResumenMetricas,
  TopProductosResponse,
  VentasPorPeriodoResponse,
} from '../types/admin-metrics.types';

function dateParams(filter: MetricsDateFilter) {
  return {
    ...(filter.desde ? { desde: filter.desde } : {}),
    ...(filter.hasta ? { hasta: filter.hasta } : {}),
  };
}

export async function getResumen(filter: MetricsDateFilter): Promise<ResumenMetricas> {
  const response = await apiClient.get<ResumenMetricas>(ENDPOINTS.adminMetricas.resumen, {
    params: dateParams(filter),
  });
  return response.data;
}

export async function getVentasPorPeriodo(
  filter: MetricsDateFilter,
  granularidad: Granularidad,
): Promise<VentasPorPeriodoResponse> {
  const response = await apiClient.get<VentasPorPeriodoResponse>(
    ENDPOINTS.adminMetricas.ventasPorPeriodo,
    { params: { ...dateParams(filter), granularidad } },
  );
  return response.data;
}

export async function getTopProductos(
  filter: MetricsDateFilter,
  top = 10,
): Promise<TopProductosResponse> {
  const response = await apiClient.get<TopProductosResponse>(
    ENDPOINTS.adminMetricas.topProductos,
    { params: { ...dateParams(filter), top } },
  );
  return response.data;
}

export async function getPedidosPorEstado(
  filter: MetricsDateFilter,
): Promise<PedidosPorEstadoResponse> {
  const response = await apiClient.get<PedidosPorEstadoResponse>(
    ENDPOINTS.adminMetricas.pedidosPorEstado,
    { params: dateParams(filter) },
  );
  return response.data;
}
