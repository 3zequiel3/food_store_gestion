import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { CategoriaRead } from '../../products/types/products.types';

/**
 * Servicio de categorías.
 * Para el catálogo del cliente solo se necesitan las categorías hoja
 * (sin hijos), que son las asignables a productos.
 */

/** GET /categorias/?solo_hojas=true — categorías sin hijos */
export async function getLeafCategories(): Promise<CategoriaRead[]> {
  const response = await apiClient.get<CategoriaRead[]>(ENDPOINTS.categorias.list, {
    params: { solo_hojas: true },
  });
  return response.data;
}
