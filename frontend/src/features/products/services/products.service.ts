import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  PaginatedProductos,
  ProductoDetail,
  ProductFilters,
} from '../types/products.types';

/**
 * Servicio de productos del catálogo.
 *
 * Todas las rutas se resuelven via ENDPOINTS — nunca hardcodeadas.
 * El backend espera `disponible=true` implícitamente para el catálogo público,
 * pero lo enviamos explícito para claridad (RN-CA08).
 */

/** GET /productos/ — listado paginado con filtros opcionales */
export async function getProducts(filters: ProductFilters = {}): Promise<PaginatedProductos> {
  const params: Record<string, string | number | boolean> = {
    page: filters.page ?? 1,
    limit: filters.limit ?? 20,
    disponible: filters.disponible ?? true,
  };

  if (filters.search) params.search = filters.search;
  if (filters.categoria_id != null) params.categoria_id = filters.categoria_id;
  if (filters.excluir_alergenos) params.excluir_alergenos = true;

  // excluir_alergeno_ids se envía como múltiples query params del mismo nombre
  const response = await apiClient.get<PaginatedProductos>(ENDPOINTS.productos.list, {
    params,
    paramsSerializer: (p) => {
      const parts: string[] = [];
      for (const [key, val] of Object.entries(p)) {
        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(val))}`);
      }
      if (filters.excluir_alergeno_ids?.length) {
        for (const id of filters.excluir_alergeno_ids) {
          parts.push(`excluir_alergeno_ids=${encodeURIComponent(id)}`);
        }
      }
      return parts.join('&');
    },
  });

  return response.data;
}

/** GET /productos/:id — detalle completo del producto */
export async function getProduct(id: number): Promise<ProductoDetail> {
  const response = await apiClient.get<ProductoDetail>(ENDPOINTS.productos.detail(id));
  return response.data;
}
